# Data Pipeline — Pachyderm Demo

## Summary

A raw CSV of ~14 500 rows is fed through a **6-block linear DAG**.
Each block is a standalone Python script running inside a Docker container.
When new data is uploaded to the input repo, Pachyderm automatically
re-executes the entire cascade and versions every intermediate result.

### What the pipeline does

```
pm3d_data ─► block1 ─► block2 ─► block3 ─► block4 ─► block5 ─► block6
             preprocess  clean    pivot    gen_mixes  extract   write_csv
```

| Block | Pipeline | Description | Rows In → Out |
|-------|----------|-------------|---------------|
| 1 | `block1_preprocess` | Rename columns, extract FileName from URL, strip whitespace, fill missing Species | 14 469 → 14 468 |
| 2 | `block2_clean_filter` | Fix species names, drop duplicates, filter to rgb + depth image types | 14 468 → 6 314 |
| 3 | `block3_reorder_pivot` | Pivot table — one row per (FileName, ImageType), species become columns | 6 314 → 1 967 |
| 4 | `block4_gen_mixes` | Add 16 boolean mix-flag columns (Rye-Clover, Wheat-Clover, etc.) | 1 967 → 1 967 |
| 5 | `block5_extract_mix` | Filter to rows matching Rye-Clover-Mix or Wheat-Clover-Mix | 1 967 → 476 |
| 6 | `block6_write_csv` | Drop all-NaN columns, export final `output.csv` | 476 → 476 |

Each block also writes three diagnostic files alongside its main output:

| File | Contents |
|------|----------|
| `stats.json` | Row counts, timestamp |
| `quality.json` | Null counts, data types, unique counts per column |
| `diff.json` | What changed — rows dropped (and why), columns added/removed, retention % |

### How the source code maps to blocks

Each block reimplements one function from `src/data_helper.py` as a
self-contained script with no cross-imports:

| Block | Source Function |
|-------|-----------------|
| 1 | `preprocess_raw_calibration_metadata()` |
| 2 | `preprocess_calibration_data()` + `test_duplicate_biomass_fnames()` |
| 3 | `reorder_calibration_metadata()` |
| 4 | `generate_popular_mixes()` |
| 5 | `extract_data_from_popular_mix()` |
| 6 | `export_results_to_csv()` |

## Prerequisites

- **Minikube** running with the Docker driver (`docker ps | grep minikube`)
- **Pachyderm 2.12.x** deployed via Helm (`helm list -A` → `pachd`)
- **pachctl** CLI installed and matching the server version
- **Docker CLI** on the host
- **kubectl** configured to talk to the minikube cluster

### 1. Fix kubeconfig (one-time)

Minikube runs inside a Docker container. The Kubernetes API-server port
(8443) is mapped to a random host port. Export the kubeconfig and patch the
server URL to point at the host-mapped port:

```bash
mkdir -p ~/.kube
docker exec minikube cat /etc/kubernetes/admin.conf > ~/.kube/config

# Find YOUR mapped port (e.g. 0.0.0.0:32771):
docker port minikube 8443

# Patch it into the kubeconfig:
sed -i 's|https://control-plane.minikube.internal:8443|https://127.0.0.1:<YOUR_PORT>|' \
  ~/.kube/config
```

Verify:

```bash
kubectl get pods          # expect 8 pods Running (pachd, etcd, console, loki, etc.)
pachctl version           # client and server versions should match (2.12.x)
```

### 2. Authenticate pachctl (one-time)

```bash
# Extract the root token from the Kubernetes secret:
kubectl get secret pachyderm-auth -o jsonpath='{.data.root-token}' | base64 -d
# Copy the output

# Authenticate (paste the token when prompted):
pachctl auth use-auth-token
```

### 3. Start the port-forward (each session)

The `pachctl` CLI talks to pachd through the proxy service.
Start a port-forward and leave it running:

```bash
kubectl port-forward svc/pachyderm-proxy 8080:80 &
```

---

## Step 1 — Build and Load the Docker Image

### Build

```bash
cd demo/pipelines
docker build -t pm3d-pipeline:v2 .
```

The Dockerfile uses `python:3.10-slim`, installs `pandas==2.2.3`,
and copies all `block*.py` scripts into `/app/`.

### Load into minikube

Minikube uses Docker-in-Docker. The local registry is not available,
so load the image directly into minikube's internal Docker daemon:

```bash
docker save pm3d-pipeline:v2 | docker exec -i minikube docker load
```

Tag it to match the fully-qualified name in the pipeline specs:

```bash
docker exec minikube docker tag pm3d-pipeline:v2 docker.io/library/pm3d-pipeline:v2
```

Verify the image is visible to the Kubernetes container runtime:

```bash
docker exec minikube crictl images | grep pm3d
# Expected:  pm3d-pipeline   v2   <image-id>   436MB
```

> **Why not `docker push`?** Minikube's built-in registry addon is not
> running. Attempting `docker push localhost:32770/...` will fail with
> "connection reset by peer". The `docker save | docker load` approach
> bypasses the registry entirely.

> **Why not `minikube image load`?** The `minikube` CLI cannot find the
> cluster profile on this host. Loading via `docker exec` works directly.

---

## Step 2 — Prepare the Data

```bash
cd demo

# Create a partial dataset (first 7 000 data rows) for a quick initial run:
head -1 data/pm3d-training-data-v4.csv >  data/pm3d_data_partial.csv
tail -n +2 data/pm3d-training-data-v4.csv | head -7000 >> data/pm3d_data_partial.csv
wc -l data/pm3d_data_partial.csv   # expect 7 001 (header + 7 000 rows)

# Create the full dataset:
cp data/pm3d-training-data-v4.csv data/pm3d_data_full.csv
wc -l data/pm3d_data_full.csv      # expect 14 470 (header + 14 469 rows)
```

---

## Step 3 — Create the Input Repo and Upload Data

```bash
pachctl create repo pm3d_data
pachctl put file pm3d_data@master:/pm3d_data.csv -f data/pm3d_data_partial.csv
```

Verify:

```bash
pachctl list repo              # pm3d_data  ~2.24 MiB
pachctl list file pm3d_data@master
# NAME             SIZE
# /pm3d_data.csv   2.24MiB
```

---

## Step 4 — Deploy the Pipelines

Create all six pipelines **in DAG order** (each block reads from the
previous block's output repo):

```bash
cd demo

pachctl create pipeline -f specs/block1_preprocess.json
pachctl create pipeline -f specs/block2_clean_filter.json
pachctl create pipeline -f specs/block3_reorder_pivot.json
pachctl create pipeline -f specs/block4_gen_mixes.json
pachctl create pipeline -f specs/block5_extract_mix.json
pachctl create pipeline -f specs/block6_write_csv.json
```

Because `pm3d_data@master` already has data, Pachyderm immediately triggers
a job for each pipeline. The jobs cascade: block1 runs first, its output
commit triggers block2, and so on.

---

## Step 5 — Monitor the Cascade

### Watch pipeline state (repeat every few seconds)

```bash
pachctl list pipeline
```

Expected progression:

```
block1_preprocess     running / success    ✓ done
block2_clean_filter   running / success    ✓ done
block3_reorder_pivot  running / running    ← processing now
block4_gen_mixes      running / starting   ← waiting for block3
block5_extract_mix    running / starting
block6_write_csv      running / starting
```

Once all six show `running / success`, the cascade is complete.

### Check pod health

```bash
kubectl get pods | grep block
# All should show 2/2 Running
```

> **Troubleshooting — `ErrImagePull` / `ImagePullBackOff`:**
>
> Kubernetes is trying to pull the image from Docker Hub instead of using
> the local copy.  This means the image was not loaded into minikube's
> Docker daemon.  Fix:
>
> ```bash
> docker save pm3d-pipeline:v2 | docker exec -i minikube docker load
> docker exec minikube docker tag pm3d-pipeline:v2 docker.io/library/pm3d-pipeline:v2
> ```
>
> Then delete the stuck pods so they restart:
>
> ```bash
> kubectl delete pods -l suite=pachyderm,pipelineName
> ```

### View output files at each stage

```bash
for repo in block1_preprocess block2_clean_filter block3_reorder_pivot \
            block4_gen_mixes block5_extract_mix block6_write_csv; do
  echo "=== $repo ==="
  pachctl list file "$repo@master"
done
```

Each stage should contain four files:

```
/cleaned.csv       (or preprocessed.csv, pivoted.csv, etc.)
/diff.json
/quality.json
/stats.json
```

### View the final output

```bash
pachctl get file block6_write_csv@master:/output.csv | head -5
pachctl get file block6_write_csv@master:/output.csv | wc -l
# Partial run: expect 317 lines (316 data rows + header)
```

### View diagnostics

```bash
# Row-level diff — what was dropped and why:
pachctl get file block2_clean_filter@master:/diff.json

# Column-level data quality:
pachctl get file block2_clean_filter@master:/quality.json

# Summary stats:
pachctl get file block2_clean_filter@master:/stats.json
```

---

## Step 6 — Upload Full Data (automatic re-run)

Replace the partial dataset with the full CSV.  Pachyderm detects the new
commit on `pm3d_data@master` and automatically re-executes every pipeline
in the DAG:

```bash
pachctl delete file pm3d_data@master:/pm3d_data.csv
pachctl put file pm3d_data@master:/pm3d_data.csv -f data/pm3d_data_full.csv
```

Monitor the cascade:

```bash
pachctl list pipeline    # watch states cascade from starting → running → success
pachctl list job         # see the new job set with progress bars
```

### Validate full-data results

```bash
# Final row count:
pachctl get file block6_write_csv@master:/output.csv | wc -l
# Expect 477 lines (476 data rows + header)

# Stats:
pachctl get file block6_write_csv@master:/stats.json
# "input_rows": 476, "output_rows": 476, 19 columns

# Diff at block2 — see exactly what was filtered:
pachctl get file block2_clean_filter@master:/diff.json
# "missing_essential_fields": 1853, "non_rgb_depth_images": 6301, "retention_pct": 43.6
```

---

## Step 7 — Explore Data Versioning

Every commit to `pm3d_data` creates a new commit in every downstream repo.
All intermediate data from all runs is preserved.

### View commit history

```bash
pachctl list commit pm3d_data
# Shows every upload: partial, delete, full

pachctl list commit block3_reorder_pivot
# Shows a matching commit for each input commit
```

### Access past versions

```bash
# Get the pivoted CSV from the partial-data run (use the commit ID from list commit):
pachctl get file block3_reorder_pivot@<commit-id>:/pivoted.csv | wc -l

# Compare sizes between runs:
pachctl list file block3_reorder_pivot@<old-commit>
pachctl list file block3_reorder_pivot@<new-commit>
```

### Inspect a specific job

```bash
pachctl inspect job block2_clean_filter@<commit-id>
# Shows: state, duration, data downloaded/uploaded, reason (if failed)
```

---

## Step 8 — Export Output to Local Filesystem

Pachyderm keeps all data inside its object store.  To pull the final CSV
onto the local filesystem:

```bash
bash export_output.sh
# → data/output_latest.csv
```

---

## Console UI

The Pachyderm Console provides a web-based view of the DAG, repos, commits,
jobs, and file contents.

### Access from a remote machine

Start an SSH tunnel from your laptop to the host running Pachyderm:

```bash
ssh -L 9080:localhost:8080 asmathew@lightning.cals.ncsu.edu
```

Then open **http://localhost:9080** in your browser.

### What you can see in the Console

| Page | How to get there | What it shows |
|------|------------------|---------------|
| **DAG view** | Landing page | `pm3d_data` → block1 → ... → block6 with status indicators |
| **Repo files** | Click a pipeline → click a commit | File list: CSV, `stats.json`, `quality.json`, `diff.json` |
| **CSV preview** | Click any `.csv` file | Rendered as a table — browse data without downloading |
| **JSON preview** | Click `diff.json` or `quality.json` | Syntax-highlighted view of diagnostics |
| **Job logs** | Click pipeline → Jobs tab → click a job | Container stdout/stderr |
| **Commit history** | Click a repo → Commits tab | Every data version with size and timestamp |

> **Tip:** If the Console shows stale data, hard-refresh your browser
> (`Ctrl+Shift+R`) and make sure you're viewing the **latest commit**
> (topmost entry), not an older one.

---

## Updating Pipeline Code

When you change a `block*.py` script, rebuild the image, reload it into
minikube, and update the pipeline:

```bash
# 1. Rebuild with a new tag:
cd demo/pipelines
docker build -t pm3d-pipeline:v3 .

# 2. Load into minikube:
docker save pm3d-pipeline:v3 | docker exec -i minikube docker load
docker exec minikube docker tag pm3d-pipeline:v3 docker.io/library/pm3d-pipeline:v3

# 3. Update the image tag in the spec file(s):
sed -i 's|pm3d-pipeline:v2|pm3d-pipeline:v3|g' specs/block*.json

# 4. Update pipelines (--reprocess forces re-execution):
for spec in specs/block*.json; do
  pachctl update pipeline -f "$spec" --reprocess
done
```

---

## Cleanup

Delete in **reverse DAG order** (downstream first), then the input repo:

```bash
pachctl delete pipeline block6_write_csv
pachctl delete pipeline block5_extract_mix
pachctl delete pipeline block4_gen_mixes
pachctl delete pipeline block3_reorder_pivot
pachctl delete pipeline block2_clean_filter
pachctl delete pipeline block1_preprocess
pachctl delete repo pm3d_data
```

---

## Starting Over (Full Reset)

To wipe everything and re-run the demo from scratch:

### 1. Delete all pipelines and repos in Pachyderm

```bash
pachctl delete pipeline block6_write_csv
pachctl delete pipeline block5_extract_mix
pachctl delete pipeline block4_gen_mixes
pachctl delete pipeline block3_reorder_pivot
pachctl delete pipeline block2_clean_filter
pachctl delete pipeline block1_preprocess
pachctl delete repo pm3d_data
```

### 2. Remove local exported data

```bash
rm -rf data/output_latest.csv data/diagnostics data/intermediate
```

### 3. Re-run the demo from Step 3

```bash
# Create the input repo
pachctl create repo pm3d_data

# Upload data (partial or full)
pachctl put file pm3d_data@master:/pm3d_data.csv -f data/pm3d_data_full.csv

# Deploy all pipelines
for spec in specs/block{1,2,3,4,5,6}_*.json; do
  pachctl create pipeline -f "$spec"
done

# Wait for the cascade to finish
watch pachctl list pipeline

# Export the result
sh export_output.sh
```

All commit history from the previous run will be gone — every repo is
created fresh, so data versioning starts over from a clean slate.

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `pachctl list pipeline` | Pipeline states and last job status |
| `pachctl list job` | All jobs with progress bars |
| `pachctl list job --pipeline <name>` | Jobs for a specific pipeline |
| `pachctl list repo` | All repos with sizes |
| `pachctl list file <repo>@master` | Files in the latest commit |
| `pachctl list commit <repo>` | Commit history for a repo |
| `pachctl get file <repo>@master:/<file>` | Download / print a file |
| `pachctl get file <repo>@<commit>:/<file>` | Download a specific version |
| `bash export_output.sh` | Export final output CSV to `data/` |
| `pachctl inspect job <pipeline>@<commit>` | Detailed job info (duration, error reason) |
| `pachctl logs --pipeline <name>` | Container stdout/stderr |
| `pachctl update pipeline -f <spec> --reprocess` | Redeploy and re-run a pipeline |
| `kubectl get pods \| grep block` | Pod-level health check |
| `kubectl describe pod <pod>` | Events (image pull errors, OOM, etc.) |
| `kubectl logs <pod> -c user` | Raw container logs from Kubernetes |
