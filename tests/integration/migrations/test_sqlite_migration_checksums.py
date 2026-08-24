"""Guard the exact bytes of immutable SQLite migration files."""

from __future__ import annotations

import hashlib
from pathlib import Path


MIGRATIONS_PATH = Path(__file__).resolve().parents[3] / 'migrations' / 'sqlite'

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
    '0014_activities.sql': 'ba267422801bcfbc4a31da5fbc2edea8f014b267af21484026b13ce9bb42b1f4',
    '0015_pipeline_activity_steps.sql': '63ff3ae6ab2e8fd1f322ba246e8ee30cd216b5b87db7e3f9bd1b6b4cda0f7f57',
    '0016_activity_loop_runs.sql': '74f01fef75b9e2007a40b7bc7891455f6e2d2b757b2486c424f4f550d821c4c7',
    '0017_activity_catalog_installations.sql': '545540d77ae10358d14a72511fd6045cd07415864bbff0948f87e388384cb2c8',
    '0018_archive_builtin_activities.sql': 'c247732633257e31c01578703b145cd987a4983f51813ffaa9dc2c634774d02d',
    '0019_flatten_approval_activities.sql': '664cea04e52bbcb824c57eb3b133748031130759b25765f5dc40f5180a42e26c',
    '0020_flatten_quiz_activities.sql': '765189cd23acee40cf99aaa0d263cba2cac7b3deeb00dc5f9281a0934f2843ea',
    '0021_flatten_direct_loop_activities.sql': '453b87a8de13621ee697dfddfac3ae22241c63eb5c2a15e03e4246631c03d8de',
    '0022_flatten_refinement_loop_activities.sql': 'e3abeac8063f32987f774e7fbd496928081c773cbb2233f5385d55ea1e587402',
    '0023_flatten_roundtable_loop_activities.sql': '337a276775f4e786a2b4e6adc9ae8b222a54ea467992f493b3d2c4ab651b9482',
    '0024_remove_activity_config_type.sql': '4b3d69fd0f64f40c039b9fc663cd5ff64b1f85210c8fce7e96357a9af7ff94a1',
    '0025_rename_activity_pipeline_titles.sql': 'c308d42f36d283e970cba711ca602c875cf617aa4c277c21b5eff50856c1aa89',
    '0026_persona_models.sql': 'd14f15e67a978e4166de6507a080f3d92d45e0123831d4508c65a017b94456dc',
    '0027_pipeline_step_dependencies.sql': '8890234d866e4c8fadeb44dddfd04dfcc7b60c51dda510bb7b2766fdc7e10b54',
    '0028_rename_pipeline_dependency_success_condition.sql': 'be2996fa5d047da5d324e025fbf04fffce9fc0b7514d2bfcb4e09a8e6e0839ea',
    '0029_activity_runs.sql': '9aff5fae10b681cd1c588d0a585825bd5e6c2a9dc98fee374426e9da71b43178',
    '0030_pipeline_runs.sql': 'ef9f73a426f846bfb3928b72b807388eb22022ab889f36c379c5fa4af894ed8d',
    '0031_linked_services.sql': '399cb66c3b888552553635427932f7593bc4212aa9b7793e7e93674d2739f54c',
    '0032_persona_linked_service_selections.sql': '4923a947721b2a190f2c8c4bf7ce7d4561907f42f9d3c0bdd238ca0552a74e47',
    '0033_pipeline_run_worker_claims.sql': 'd326ceb9e751ab085f2f9ae87e923300357e960beaf637340004401930907252',
    '0034_pipeline_run_commit_mode.sql': '52c030f8a4c0cff290abb586dcce45e4cc8e66b623ca1d97faf08c8eaad90b72',
    '0035_remove_legacy_loops.sql': 'bf4cf4ec334c6b52e00bc243b3c91611e6373b42baf2905c1331d19162853daa',
    '0036_pipeline_run_events_and_gates.sql': 'df75d045a0b973f63fbe411bd318540d1749a1016091774e57fc589992426127',
    '0037_unify_human_activity_runs.sql': '07bd99705142318f3e18e9e1ad399e0de7d1e174e82f0a813b8078300e99c0f9',
    '0038_prepared_pipeline_runs.sql': 'a829c560010eab5a7c88969acb380b2c819d6cd9a0d04fac031c39b0ce2dab0d',
    '0039_workers.sql': '8c8fd031d67e718903a9e77af0bbefde9427b855882a21514eb297554710f1db',
    '0040_retire_legacy_provider_credentials.sql': 'd278ba81730874bfa717f3152aff0b21410cea26d767fa610808f5f43ca8926f',
    '0041_pipeline_harness.sql': '8bbd7a703c01025dfaf0f3988af9b167fce5759e852b95e811b977fb8f901a3a',
    '0042_worker_harnesses.sql': '12904d2b0b1f7ceae8974ff65c9a694b7ad95fd844ebfbac1b7a2f1d5eeb8564',
}


def test_sqlite_migration_files_match_immutable_checksum_manifest() -> None:
    """Source migrations match their approved byte-for-byte checksums."""

    actual_checksums = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in MIGRATIONS_PATH.glob('*.sql')
    }

    assert actual_checksums == EXPECTED_CHECKSUMS
