"""Numeric Spark factor import with explicit source and application identities."""
import math
from pathlib import Path
from ml.common.artifacts import read_json, safe_path, sha256


class FactorStore:
    def __init__(self, users, items, source_to_movie, rank, regularization):
        self.users, self.items, self.source_to_movie = users, items, source_to_movie
        self.rank, self.regularization = rank, regularization
        if type(rank) is not int or not 1 <= rank <= 128 or isinstance(regularization, bool) or not isinstance(regularization, (int, float)) or not math.isfinite(regularization) or regularization <= 0:
            raise ValueError("Valid frozen ALS rank/regularization is required.")
        if len(set(source_to_movie.values())) != len(source_to_movie):
            raise ValueError("Canonical factor mapping must not silently merge conflicting items.")
        for table in (users, items):
            for identifier, vector in table.items():
                if type(identifier) is not int or not 1 <= identifier <= 2147483647 or len(vector) != rank or any(not math.isfinite(value) for value in vector):
                    raise ValueError("Invalid Spark Int32 factor ID/dimension/value.")

    @classmethod
    def load(cls, directory, mapping_path, workspace=None):
        root = Path(workspace or Path(__file__).resolve().parents[1]).resolve()
        directory = safe_path(directory, root)
        mapping_path = safe_path(mapping_path, root)
        manifest, mapping = read_json(directory / "factor_manifest.json"), read_json(mapping_path)
        if manifest.get("source_namespace") != "movielens" or mapping.get("source_namespace") != "movielens" or mapping.get("mapping_approved") is not True or not mapping.get("reviewed_by"):
            raise ValueError("Approved canonical mapping and MovieLens source namespace required.")
        files = manifest.get("files_sha256", {})
        actual = {path.relative_to(directory).as_posix() for name in ("user_factors", "item_factors")
                  for path in (directory / name).rglob("*.parquet")}
        if not files or actual != set(files):
            raise ValueError("Every factor Parquet part requires a recorded hash.")
        for name, checksum in files.items():
            path = (directory / name).resolve()
            if not path.is_relative_to(directory) or sha256(path) != checksum:
                raise ValueError("Factor fingerprint mismatch.")
        import pyarrow.dataset as ds
        def load_parts(name, maximum):
            result = {}
            scanner = ds.dataset(directory / name, format="parquet").scanner(columns=["id", "features"], batch_size=4096)
            for batch in scanner.to_batches():
                for row in batch.to_pylist():
                    if row["id"] in result or len(result) >= maximum:
                        raise ValueError("Duplicate or oversized factor table.")
                    result[row["id"]] = row["features"]
            return result
        pairs = mapping.get("source_to_movie", {})
        if any(not isinstance(value, str) or not value for value in pairs.values()):
            raise ValueError("Canonical movie identifiers are required.")
        if any(not isinstance(key, str) or not key.isdecimal() or str(int(key)) != key for key in pairs):
            raise ValueError("Source item keys must be canonical decimal MovieLens IDs.")
        from dataset_tools.recordio import load_registry
        registry = safe_path(mapping["canonical_registry_path"], root)
        if sha256(registry) != mapping.get("canonical_registry_sha256"):
            raise ValueError("Approved canonical registry fingerprint differs.")
        canonical_ids, blockers = load_registry(registry)
        if blockers or set(pairs.values()) - canonical_ids:
            raise ValueError("Factor mapping includes unapproved canonical identities.")
        return cls(load_parts("user_factors", 300000), load_parts("item_factors", 150000),
                   {int(key): value for key, value in pairs.items()}, manifest["rank"], manifest["regularization"])

    def scores(self, source_user=None, application_vector=None):
        if application_vector is not None:
            vector = application_vector
        elif isinstance(source_user, str) and source_user.startswith("movielens:"):
            vector = self.users.get(int(source_user.split(":", 1)[1]))
        else:
            # Application accounts do not borrow numeric MovieLens identities.
            return {}
        if vector is None:
            return {}
        if len(vector) != self.rank or any(not math.isfinite(value) for value in vector):
            raise ValueError("User factor dimensions differ.")
        return {self.source_to_movie[item]: sum(a * b for a, b in zip(vector, factors))
                for item, factors in self.items.items() if item in self.source_to_movie}

    def fold_in(self, ratings, approval):
        if approval.get("fold_in_method_approved") is not True or not approval.get("reviewed_by"):
            raise ValueError("App-user fold-in strategy requires explicit methodological approval.")
        reverse = {movie: source for source, movie in self.source_to_movie.items()}
        selected = [(self.items[reverse[movie]], value) for movie, value in ratings.items()
                    if movie in reverse and reverse[movie] in self.items]
        if len(selected) < 3:
            return None
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0.5 <= value <= 5 for _, value in selected):
            raise ValueError("Actual explicit ratings within0.5..5 required.")
        import numpy as np
        matrix = np.asarray([vector for vector, _ in selected], dtype=np.float64)
        target = np.asarray([value for _, value in selected], dtype=np.float64)
        # Spark explicit ALS-WR objective scales lambda by observed item count.
        return np.linalg.solve(matrix.T @ matrix + self.regularization * len(selected) * np.eye(self.rank), matrix.T @ target).tolist()
