from pathlib import Path
from typing import List, Literal, Optional, TypedDict, Union

from openparse import tables, text, consts
from openparse.pdf import Pdf
from openparse.processing import ProcessingStep, default_pipeline, run_pipeline
from openparse.schemas import Node, TableElement, TextElement, ParsedDocument


class TableTransformersArgsDict(TypedDict, total=False):
    parsing_algorithm: Literal["table-transformers"]
    min_table_confidence: float
    min_cell_confidence: float
    table_output_format: Literal["str", "markdown", "html"]


class PyMuPDFArgsDict(TypedDict, total=False):
    parsing_algorithm: Literal["pymupdf"]
    table_output_format: Literal["str", "markdown", "html"]


def _table_args_dict_to_model(
    args_dict: Union[TableTransformersArgsDict, PyMuPDFArgsDict]
) -> Union[tables.TableTransformersArgs, tables.PyMuPDFArgs]:
    if args_dict["parsing_algorithm"] == "table-transformers":
        return tables.TableTransformersArgs(**args_dict)
    elif args_dict["parsing_algorithm"] == "pymupdf":
        return tables.PyMuPDFArgs(**args_dict)
    else:
        raise ValueError(
            f"Unsupported parsing_algorithm: {args_dict['parsing_algorithm']}"
        )


class DocumentParser:
    """
    A parser for extracting elements from PDF documents, including text and tables.

    Attributes:
        processing_pipeline (Optional[List[ProcessingStep]]): A list of steps to process the extracted elements.
        table_args (Optional[Union[TableTransformersArgsDict, PyMuPDFArgsDict]]): Arguments to customize table parsing.
    """

    def __init__(
        self,
        processing_pipeline: Optional[List[ProcessingStep]] = None,
        table_args: Union[TableTransformersArgsDict, PyMuPDFArgsDict, None] = None,
    ):

        if not processing_pipeline:
            processing_pipeline = default_pipeline

        self.table_args = table_args

    def parse(
        self,
        file: str | Path,
    ) -> ParsedDocument:
        doc = Pdf(file)

        text_elems = text.ingest(doc)
        text_nodes = self._elems_to_nodes(text_elems)

        table_nodes = []
        table_args_obj = None
        if self.table_args:
            table_args_obj = _table_args_dict_to_model(self.table_args)
            table_elems = tables.ingest(doc, table_args_obj)
            table_nodes = self._elems_to_nodes(table_elems)

        nodes = text_nodes + table_nodes
        processed_nodes = run_pipeline(nodes)

        parsed_doc = ParsedDocument(
            nodes=processed_nodes,
            filename=Path(file).name,
            num_pages=doc.num_pages,
            coordinate_system=consts.COORDINATE_SYSTEM,
            table_parsing_kwargs=(
                table_args_obj.model_dump() if table_args_obj else None
            ),
        )
        return parsed_doc

    @staticmethod
    def _elems_to_nodes(
        elems: Union[List[TextElement], List[TableElement]],
    ) -> List[Node]:
        return [
            Node(
                elements=(e,),
            )
            for e in elems
        ]