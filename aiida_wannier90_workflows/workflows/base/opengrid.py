"""Wrapper workchain for OpengridCalculation to automatically handle several errors."""
import pathlib
import typing as ty

from aiida import orm
from aiida.common.lang import type_check
from aiida.engine import process_handler
from aiida.engine.processes.builder import ProcessBuilder

from aiida_quantumespresso.calculations.opengrid import OpengridCalculation
from aiida_quantumespresso.workflows.protocols.utils import ProtocolMixin

from .qebaserestart import QeBaseRestartWorkChain

__all__ = [
    "OpengridBaseWorkChain",
]


class OpengridBaseWorkChain(ProtocolMixin, QeBaseRestartWorkChain):
    """Workchain to run a opengrid calculation with automated error handling and restarts."""

    _process_class = OpengridCalculation
    _inputs_namespace = "opengrid"

    @classmethod
    def get_protocol_filepath(cls) -> pathlib.Path:
        """Return the ``pathlib.Path`` to the ``.yaml`` file that defines the protocols."""
        from importlib_resources import files

        from .. import protocols

        return files(protocols) / "base" / "opengrid.yaml"

    @classmethod
    def get_builder_from_protocol(
        cls,
        code: ty.Union[orm.Code, str, int],
        *,
        protocol: str = None,
        overrides: dict = None
    ) -> ProcessBuilder:
        """Return a builder prepopulated with inputs selected according to the chosen protocol.

        :param code: [description]
        :type code: ty.Union[orm.Code, str, int]
        :param protocol: [description], defaults to None
        :type protocol: str, optional
        :param overrides: [description], defaults to None
        :type overrides: dict, optional
        :return: [description]
        :rtype: ProcessBuilder
        """
        from aiida_quantumespresso.workflows.protocols.utils import recursive_merge

        if isinstance(code, (int, str)):
            code = orm.load_code(code)

        type_check(code, orm.Code)

        inputs = cls.get_protocol_inputs(protocol, overrides)

        metadata = inputs[cls._inputs_namespace]["metadata"]

        # If overrides are provided, they take precedence over default protocol
        if overrides:
            metadata_overrides = overrides.get(cls._inputs_namespace, {}).get(
                "metadata", {}
            )
            metadata = recursive_merge(metadata, metadata_overrides)

        # pylint: disable=no-member
        builder = cls.get_builder()
        builder[cls._inputs_namespace]["code"] = code
        builder[cls._inputs_namespace]["metadata"] = metadata
        if "settings" in inputs[cls._inputs_namespace]:
            builder[cls._inputs_namespace]["settings"] = orm.Dict(
                dict=inputs[cls._inputs_namespace]["settings"]
            )
        if "settings" in inputs:
            builder["settings"] = orm.Dict(dict=inputs["settings"])
        builder["clean_workdir"] = orm.Bool(inputs["clean_workdir"])
        # pylint: enable=no-member

        return builder

    @process_handler(
        exit_codes=[_process_class.exit_codes.ERROR_OUTPUT_STDOUT_INCOMPLETE]
    )  # pylint: disable=no-member
    def handle_output_stdout_incomplete(self, calculation):
        """Overide parent function."""
        return super().handle_output_stdout_incomplete(calculation)
