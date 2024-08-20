import docker
import os
# Initialize Docker client
client = docker.from_env()

# Docker image name
image_name = "huyouare/swebench-lite:sweb.eval.x86_64.sympy__sympy-24909"

# Command to run inside the container
command = ["python", "/testbed/harness-local/custom_script.py"]

# Pull the Docker image
print(f"Pulling image: {image_name}")
client.images.pull(image_name)

# Run the container and execute the command
print("Running container...")
host_folder_path = "/home/azureuser/SWE-harness-local/"
container = client.containers.run(
    image_name,
    command,
    detach=True,
    stdout=True,
    stderr=True,
    volumes={
        os.path.abspath(host_folder_path): {"bind": "/testbed/harness-local", "mode": "ro"}
    },
)

# Wait for the container to finish
print("Waiting for container to complete...")
exit_code = container.wait()
output = container.logs()

# Get the output
output = output.decode("utf-8")
print(f"Container output:\n{output}")

# Remove the container
container.remove()