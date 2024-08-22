import docker
import os
import time

# Initialize Docker client
start = time.time()
client = docker.from_env()

# Docker image name
image_name = "huyouare/swebench-lite:sweb.eval.x86_64.sympy__sympy-24909"
target_id = image_name.split(".")[-1]
# Commands to run inside the container
result_folder = "/testbed/local/SWE-harness-local/results/" + target_id + "/"
commands = [
    "apt-get update",
    "apt-get install -y --no-install-recommends curl",
    "rm -rf /var/lib/apt/lists/*",
    "curl -sSL https://install.python-poetry.org | python3 -",
    "poetry config virtualenvs.create false",
    "poetry install --no-interaction --no-ansi",
    'export PATH="/root/.local/bin:$PATH"',
    # "".join(command),
    "poetry install",
    "cd local/Agentless && poetry install",
    f"echo '---- localizing files .... {result_folder}'",
    f"mkdir -p {result_folder}",
    f"poetry run python agentless/fl/localize.py --file_level --target_id {target_id} --output_folder {result_folder}/file_level ",
    "echo 'localizing related levels ....'",
    f"poetry run python agentless/fl/localize.py --related_level \
                                --output_folder {result_folder}/related_level \
                                --target_id {target_id}\
                                --start_file {result_folder}/file_level/loc_outputs.jsonl \
                                --top_n 3 --compress",
    f"echo '---- localizing fine_grain_line_level levels ....'",
    f"poetry run python agentless/fl/localize.py --fine_grain_line_level \
                                --output_folder {result_folder}/edit_location \
                                --target_id {target_id}\
                                --start_file {result_folder}/related_level/loc_outputs.jsonl \
                                --top_n 3 --context_window=10",
    f"echo '---- localizing fine_grain_line_level levels ....'",
    f"poetry run python agentless/fl/localize.py --fine_grain_line_level \
                                --output_folder {result_folder}/edit_location_samples \
                                --target_id {target_id}\
                                --start_file {result_folder}/related_level/loc_outputs.jsonl \
                                --top_n 3 --context_window=10 --temperature 0.8 \
                                --num_samples 4",
    f"echo '---- localizing Merging levels ....'",
    f"poetry run python agentless/fl/localize.py --merge \
                                --output_folder {result_folder}/edit_location_samples_merged \
                                --target_id {target_id}\
                                --start_file {result_folder}/edit_location_samples/loc_outputs.jsonl \
                                --num_samples 4",
    f"echo '---- localizing repair levels ....'",
    f"poetry run python agentless/repair/repair.py --loc_file {result_folder}/location/loc_outputs.jsonl \
                                  --output_folder {result_folder}/repair \
                                  --target_id {target_id}\
                                  --loc_interval --top_n=3 --context_window=10 \
                                  --max_samples 10  --cot --diff_format \
                                  --gen_and_process",
    f"echo '---- localizing ranking levels ....'",
    f"poetry run python agentless/repair/rerank.py --patch_folder {result_folder} --num_samples 10 --deduplicate --plausible",
    #"Patch it code and then we can run test"

]

# Create a shell script with the commands
script_content = "\n".join(commands)
script_path = f"scripts/run_{target_id}.sh"

with open(script_path, "w") as script_file:
    script_file.write(script_content)

# Pull the Docker image
print(f"Pulling image: {image_name}")
client.images.pull(image_name)

# Run the container and execute the command
print("Running container...")
host_folder_path = "/home/azureuser/"
container = client.containers.run(
    image_name,
    [
        "sh",
        "-c",
        f"chmod +x /testbed/local/SWE-harness-local/{script_path} && /testbed/local/SWE-harness-local/{script_path}",
    ],
    detach=True,
    stdout=True,
    stderr=True,
    volumes={
        os.path.abspath(host_folder_path): {"bind": "/testbed/local", "mode": "rw"}
    },
)

# Wait for the container to finish
print("Waiting for container to complete...")
exit_code = container.wait()
output = container.logs()

# Get the output
output = output.decode("utf-8")
print(f"Container output:\n{output}")
# with open(f"/testbed/local/SWE-harness-local/logs/{target_id}_final_output.log", "w+") as f:
#     f.write(output)

container.remove()
print(f"Finished task in {time.time() - start}")

