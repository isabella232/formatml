from argparse import ArgumentParser
from pathlib import Path
from typing import List

from asdf import open as asdf_open

from formatml.data.fields.binary_label_field import BinaryLabelsField
from formatml.data.fields.indexes_field import IndexesField
from formatml.data.fields.internal_type_field import InternalTypeField
from formatml.data.fields.length_field import LengthField
from formatml.data.fields.metadata_field import MetadataField
from formatml.data.fields.roles_field import RolesField
from formatml.data.fields.typed_dgl_graph_field import TypedDGLGraphField
from formatml.data.instance import Instance
from formatml.data.types.codrep_label import CodRepLabel
from formatml.parsing.parser import Nodes
from formatml.pipelines.codrep.cli_builder import CLIBuilder
from formatml.pipelines.pipeline import register_step
from formatml.utils.config import Config
from formatml.utils.helpers import setup_logging


def add_arguments_to_parser(parser: ArgumentParser) -> None:
    cli_builder = CLIBuilder(parser)
    cli_builder.add_uasts_dir()
    cli_builder.add_instance_file()
    cli_builder.add_configs_dir()
    parser.add_argument(
        "--encoder-edge-types",
        help="Edge types to use in the graph encoder (defaults to %(default)s).",
        nargs="+",
        default=["child", "parent", "previous_token", "next_token"],
    )
    parser.add_argument(
        "--max-length",
        help="Maximum token length to consider before clipping "
        "(defaults to %(default)s).",
        type=int,
        default=128,
    )


@register_step(pipeline_name="codrep", parser_definer=add_arguments_to_parser)
def index(
    *,
    uasts_dir: str,
    instance_file: str,
    configs_dir: str,
    encoder_edge_types: List[str],
    max_length: int,
    log_level: str,
) -> None:
    """Index UASTs with respect to some fields."""
    Config.from_arguments(locals(), ["uasts_dir", "instance_file"], "configs_dir").save(
        Path(configs_dir) / "index.json"
    )
    logger = setup_logging(__name__, log_level)

    uasts_dir_path = Path(uasts_dir).expanduser().resolve()
    instance_file_path = Path(instance_file).expanduser().resolve()

    instance = Instance(
        fields=[
            TypedDGLGraphField(
                name="typed_dgl_graph", type="graph", edge_types=encoder_edge_types
            ),
            MetadataField(name="metadata", type="metadata"),
            BinaryLabelsField(name="label", type="label"),
            IndexesField(name="indexes", type="indexes"),
            InternalTypeField(name="internal_type", type="input"),
            RolesField(name="roles", type="input"),
            LengthField(name="max_length", type="input", max_length=max_length),
        ]
    )

    logger.info(f"Indexing %s", uasts_dir_path)
    for file_path in uasts_dir_path.rglob("*.asdf"):
        with asdf_open(str(file_path)) as af:
            instance.index(
                {
                    Nodes: Nodes.from_tree(af.tree["nodes"]),
                    CodRepLabel: CodRepLabel.from_tree(af.tree["codrep_label"]),
                    str: af.tree["filepath"],
                }
            )
    instance.save(instance_file_path)
    logger.info(f"Indexed  %s", uasts_dir_path)
