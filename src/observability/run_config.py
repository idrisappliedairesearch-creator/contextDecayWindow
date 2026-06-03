from dataclasses import dataclass


@dataclass
class RunConfig:
    condition: str
    run_id: str
    output_dir: str
    study_dir: str
