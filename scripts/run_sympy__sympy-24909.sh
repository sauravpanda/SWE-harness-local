apt-get update
apt-get install -y --no-install-recommends curl
rm -rf /var/lib/apt/lists/*
curl -sSL https://install.python-poetry.org | python3 -
poetry config virtualenvs.create false
poetry install --no-interaction --no-ansi
export PATH="/root/.local/bin:$PATH"
poetry install
cd local/Agentless && poetry install
echo '---- localizing files .... /testbed/local/SWE-harness-local/results/sympy__sympy-24909/'
mkdir -p /testbed/local/SWE-harness-local/results/sympy__sympy-24909/
poetry run python agentless/fl/localize.py --file_level --target_id sympy__sympy-24909 --output_folder /testbed/local/SWE-harness-local/results/sympy__sympy-24909//file_level 
echo 'localizing related levels ....'
poetry run python agentless/fl/localize.py --related_level                                 --output_folder /testbed/local/SWE-harness-local/results/sympy__sympy-24909//related_level                                 --target_id sympy__sympy-24909                                --start_file /testbed/local/SWE-harness-local/results/sympy__sympy-24909//file_level/loc_outputs.jsonl                                 --top_n 3 --compress
echo '---- localizing fine_grain_line_level levels ....'
poetry run python agentless/fl/localize.py --fine_grain_line_level                                 --output_folder /testbed/local/SWE-harness-local/results/sympy__sympy-24909//edit_location                                 --target_id sympy__sympy-24909                                --start_file /testbed/local/SWE-harness-local/results/sympy__sympy-24909//related_level/loc_outputs.jsonl                                 --top_n 3 --context_window=10
echo '---- localizing fine_grain_line_level levels ....'
poetry run python agentless/fl/localize.py --fine_grain_line_level                                 --output_folder /testbed/local/SWE-harness-local/results/sympy__sympy-24909//edit_location_samples                                 --target_id sympy__sympy-24909                                --start_file /testbed/local/SWE-harness-local/results/sympy__sympy-24909//related_level/loc_outputs.jsonl                                 --top_n 3 --context_window=10 --temperature 0.8                                 --num_samples 4
echo '---- localizing Merging levels ....'
poetry run python agentless/fl/localize.py --merge                                 --output_folder /testbed/local/SWE-harness-local/results/sympy__sympy-24909//edit_location_samples_merged                                 --target_id sympy__sympy-24909                                --start_file /testbed/local/SWE-harness-local/results/sympy__sympy-24909//edit_location_samples/loc_outputs.jsonl                                 --num_samples 4
echo '---- localizing repair levels ....'
poetry run python agentless/repair/repair.py --loc_file /testbed/local/SWE-harness-local/results/sympy__sympy-24909//location/loc_outputs.jsonl                                   --output_folder /testbed/local/SWE-harness-local/results/sympy__sympy-24909//repair                                   --target_id sympy__sympy-24909                                  --loc_interval --top_n=3 --context_window=10                                   --max_samples 10  --cot --diff_format                                   --gen_and_process
echo '---- localizing ranking levels ....'
poetry run python agentless/repair/rerank.py --patch_folder /testbed/local/SWE-harness-local/results/sympy__sympy-24909/ --num_samples 10 --deduplicate --plausible