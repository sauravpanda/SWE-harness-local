import docker
import os
import json
import shutil
import jsonlines
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from swebench.harness.run_evaluation import main as run_swebench

# List of Docker images to run
docker_images = [
    "huyouare/swebench-lite:sweb.eval.x86_64.sympy__sympy-24909",
]

# Base output directory
base_output_dir = "docker_outputs"
os.makedirs(base_output_dir, exist_ok=True)

# Initialize Docker client
client = docker.from_env()


def run_swebench(predictions_path, run_id, workers, shard):
    print(f"Processing shard {shard['shard_id']} with {workers} workers")

    shard_predictions_path = f"/tmp/shard_{shard['shard_id']}.jsonl"

    os.makedirs(os.path.dirname(shard_predictions_path), exist_ok=True)
    with jsonlines.open(shard_predictions_path, mode="w") as writer:
        writer.write_all(shard["data"])

    print(f"Running SWEBench on shard {shard['shard_id']}")
    try:
        swebench_results = run_swebench(
            dataset_name="princeton-nlp/SWE-bench_Lite",
            split="test",
            instance_ids=None,
            predictions_path=shard_predictions_path,
            max_workers=workers,
            open_file_limit=4096,
            timeout=1800,
            force_rebuild=False,
            cache_level="env",
            clean=False,
            run_id=f"{run_id}_shard_{shard['shard_id']}",
        )
    except Exception as e:
        print(f"Error occurred: {e}")
        swebench_results = None

    print(f"SWEBench results for shard {shard['shard_id']}: {swebench_results}")

    return {
        "shard_id": shard["shard_id"],
        "swebench_results": swebench_results,
        "metadata": {
            "predictions_path": predictions_path,
            "run_id": run_id,
            "workers": workers,
        },
    }


def create_shards(predictions_path, num_shards):
    print(f"Creating {num_shards} shards from {predictions_path}")
    shards = []
    with jsonlines.open(predictions_path) as reader:
        for i, data_item in enumerate(reader):
            shard_id = i // (len(reader) // num_shards)
            if len(shards) <= shard_id:
                shards.append({"shard_id": shard_id, "data": []})
            shards[shard_id]["data"].append(data_item)
    return shards


def combine_results(results):
    print(f"Combining {len(results)} results")
    combined = {}
    for i, result in enumerate(results):
        combined[f"shard_{i}"] = result
    return combined


def run_swebench_evaluation(
    predictions_path, run_id, num_shards=10, workers_per_shard=4
):
    shards = create_shards(predictions_path, num_shards)

    with ProcessPoolExecutor(max_workers=num_shards) as executor:
        results = list(
            executor.map(
                run_swebench,
                [predictions_path] * num_shards,
                [run_id] * num_shards,
                [workers_per_shard] * num_shards,
                shards,
            )
        )

    combined_results = combine_results(results)

    print(f"Processing completed for run_id: {run_id}")
    return combined_results


def run_docker_image(image_name, output_dir, predictions_file_pattern):
    print(f"Running image: {image_name}")

    client.images.pull(image_name)

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Get the absolute path of the output directory
    abs_output_dir = os.path.abspath(output_dir)

    # Run the container
    container = client.containers.run(
        image_name,
        stdin_open=True,
        tty=True,
        detach=False,
        volumes={abs_output_dir: {"bind": "/app/output", "mode": "rw"}},
    )

    # Wait for the container to finish
    container.wait()

    # Get container logs
    logs = container.logs().decode("utf-8")

    # Save logs to file
    log_filename = os.path.join(output_dir, "container.log")
    with open(log_filename, "w") as log_file:
        log_file.write(logs)

    print(f"Logs saved to: {log_filename}")

    # Copy any generated files from the container to the output directory
    try:
        # Create a tarball of the /app/output directory in the container
        bits, stat = container.get_archive("/app/output")

        # Save the tarball locally
        tarball_path = os.path.join(output_dir, "output.tar")
        with open(tarball_path, "wb") as f:
            for chunk in bits:
                f.write(chunk)

        # Extract the tarball
        shutil.unpack_archive(tarball_path, output_dir)

        # Remove the tarball
        os.remove(tarball_path)

        print(f"Generated files copied to: {output_dir}")
    except Exception as e:
        print(f"Error copying files: {str(e)}")

    # Remove the container
    container.remove()

    # Run SWE-bench evaluation on the generated files
    predictions_paths = [
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if predictions_file_pattern in f
    ]
    for predictions_path in predictions_paths:
        run_id = f"{image_name.replace('/', '_')}_{os.path.basename(output_dir)}"
        results = run_swebench_evaluation(predictions_path, run_id)

        # Save SWE-bench results
        results_filename = os.path.join(output_dir, "swebench_results.json")
        with open(results_filename, "w") as f:
            json.dump(results, f, indent=2)

        print(f"SWE-bench results saved to: {results_filename}")
        run_id = f"{image_name.replace('/', '_')}_{os.path.basename(output_dir)}"
        results = run_swebench_evaluation(predictions_path, run_id)

        # Save SWE-bench results
        results_filename = os.path.join(output_dir, "swebench_results.json")
        with open(results_filename, "w") as f:
            json.dump(results, f, indent=2)

        print(f"SWE-bench results saved to: {results_filename}")


# Run each Docker image
for image in docker_images:
    try:
        # Create a unique output directory for this run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(
            base_output_dir, f"{image.replace('/', '_').replace(':', '-')}"
        )
        os.makedirs(output_dir, exist_ok=True)

        # Specify the pattern for the predictions file
        predictions_file_pattern = "all_preds.jsonl"

        run_docker_image(image, output_dir, predictions_file_pattern)
    except Exception as e:
        print(f"Error running {image}: {str(e)}")

print("All images processed.")
