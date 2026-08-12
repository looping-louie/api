"""Guard the exact bytes of immutable SQLite migration files."""

from __future__ import annotations

import hashlib
from pathlib import Path


MIGRATIONS_PATH = Path(__file__).resolve().parents[2] / 'migrations' / 'sqlite'

EXPECTED_CHECKSUMS = {
    '0001_tenants.sql': 'dd4f59d728ca96da8090ab956b23d1c8ee23055097c6ce9aa01023854191a060',
    '0002_instructions.sql': 'b23f187b0e4ecca90258a2d0d59f0f20900d73b1e9c6f7742cb8ed44daefe797',
    '0004_provider_credentials.sql': '5ea51a9902cf8589d638e7f238d2435e43105ea89504b1975de718cdb2c1f079',
    '0005_instruction_catalog.sql': 'e7c369bc499122576dcde00129da1ebe9c12ea1b0edb153b1da36f540a7dd102',
    '0006_loops.sql': '33da35851d4a71b5de0ab7ce057b68af3e64e1bf4caaad4532ad50fa84faa6cc',
    '0007_persona_skills.sql': 'dac9a0dc5575c25eaf3aa5911780884a7de71626a22066dad440018ffa5f72e6',
    '0008_loop_catalog_installations.sql': '835d540fec9a82803bfac3f1574d53a891d375afd50f1f9d93f71e7ae82b48c0',
    '0009_pipelines.sql': 'aa37b05167a65d68092536d787da257d708617072fbb17a1ff7c17e97df2d4f9',
    '0010_loop_runs.sql': 'ce76c4a166f0000972a882e5c493d0b3a870454fc217f3410964cdf1bba3abea',
    '0011_loop_run_checkpoints.sql': 'b8e9eacfd52da0438a8dac747cf77e13b92b066a1ec5d8f10d42d3b25d306ad3',
    '0012_expand_loop_run_states.sql': '0e2c0d72f6fd8a8aa6d103b7dda5dbb9c3dc773e103b4278ad7f068bc7e70fc8',
    '0013_repair_loop_run_idempotency.sql': 'fe367df6b131dbf944c053008f324cc4faf103656c6091745ab1808fba597e62',
}


def test_sqlite_migration_files_match_immutable_checksum_manifest() -> None:
    """Source migrations match their approved byte-for-byte checksums."""

    actual_checksums = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in MIGRATIONS_PATH.glob('*.sql')
    }

    assert actual_checksums == EXPECTED_CHECKSUMS
