from dataclasses import dataclass
import hashlib
from pathlib import Path
from ml.common.artifacts import read_json, safe_path, sha256
from ml.common.data import _rows


@dataclass(frozen=True)
class ThemeExample:
    record_id: str
    text: str
    targets: tuple[float, ...]
    language_code: str
    movie_id: str
    group_id: str


@dataclass
class ThemeBundle:
    labels: dict
    records: dict
    manifest_hashes: dict

    def summary(self):
        return {"labels": self.labels, "manifest_hashes": self.manifest_hashes,
            "splits": {split: {"count": len(rows), "positive_support": {name: sum(row.targets[index] for row in rows)
                for name, index in self.labels.items()}} for split, rows in self.records.items()}}


def load_config(path):
    path = Path(path).resolve()
    config = read_json(path)
    if config.get("schema_version") != 1 or config.get("task") != "themes":
        raise ValueError("An explicit multi-label theme configuration is required.")
    root = Path(config.get("workspace") or Path(__file__).resolve().parents[2]).resolve()
    taxonomy = read_json(root / "configs/data/annotations.json")
    config.update(_workspace=root, _config_path=path,
        taxonomy={"version": "movie-themes-v1", "themes": taxonomy["themes"]},
        labels={name: index for index, name in enumerate(taxonomy["themes"])})
    return config


def load_experiment(config):
    from dataset_tools.recordio import load_registry
    root, data = config["_workspace"], config["data"]
    registry = safe_path(data["canonical_registry_path"], root)
    movie_ids, blockers = load_registry(registry)
    if blockers:
        raise ValueError("Canonical movie registry is not approved.")
    hashes = {"canonical_registry": sha256(registry), "taxonomy": sha256(root / "configs/data/annotations.json")}
    records, owners, total = {}, {}, 0
    for split in ("train", "tuning", "calibration", "test"):
        path = safe_path(data["manifests"][split], root)
        hashes[split] = sha256(path)
        rows = []
        for row in _rows(path):
            if len(rows) >= 10000 or row.get("split") != split or row.get("themes_complete") is not True:
                raise ValueError("Complete frozen theme labels and bounded splits are required.")
            if row.get("training_permitted") is not True or row.get("is_synthetic") is not False or row.get("is_deleted") is not False or not row.get("consent_or_license_ref") or row.get("annotation_status") != "adjudicated" or not row.get("adjudicator_id"):
                raise ValueError("Legitimate adjudicated theme permissions are required.")
            text, identifier, group = row.get("text"), row.get("record_id"), row.get("group_id")
            if not isinstance(text, str) or not text.strip() or len(text) > 20000 or not isinstance(identifier, str) or not identifier or not isinstance(group, str) or not group:
                raise ValueError("Invalid theme text/identity/group.")
            checksum = hashlib.sha256(text.encode()).hexdigest()
            movie = str(row.get("movie_id"))
            if checksum != row.get("text_sha256") or movie not in movie_ids or row.get("language_code") not in config["language_scope"]:
                raise ValueError("Theme original hash/movie/language mismatch.")
            labels = row.get("theme_labels")
            if not isinstance(labels, list) or len(set(labels)) != len(labels) or set(labels) - set(config["labels"]):
                raise ValueError("Unknown or duplicate genuine theme labels.")
            total += len(text.encode())
            if total > 128 * 1024**2:
                raise ValueError("Theme text budget exceeded.")
            for key in (("id", identifier), ("group", group), ("movie", movie), ("text", checksum),
                        ("normalized", " ".join(text.casefold().split()))):
                if key in owners and (owners[key] != split or key[0] == "id"):
                    raise ValueError("Theme identity/group/movie/text leakage.")
                owners[key] = split
            rows.append(ThemeExample(identifier, text, tuple(float(name in labels) for name in config["labels"]),
                                     row["language_code"], movie, group))
        if not rows or sha256(path) != hashes[split]:
            raise ValueError("Empty or changed theme manifest.")
        if split == "train" and any({row.targets[index] for row in rows} != {0.0, 1.0} for index in config["labels"].values()):
            raise ValueError("Every configured theme requires genuine positive and negative training support; review taxonomy coverage.")
        records[split] = rows
    return ThemeBundle(config["labels"], records, hashes)
