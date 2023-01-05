"""The setup for the sphinx extension."""
from typing import Any, Dict

from sphinx.application import Sphinx
from sphinx.environment import BuildEnvironment

from myst_parser.sphinx_ext.references import MystDomain
from myst_parser.warnings_ import MystWarnings

DEPRECATED = "__deprecated__"


def setup_sphinx(app: Sphinx, load_parser=False):
    """Initialize all settings and transforms in Sphinx."""
    # we do this separately to setup,
    # so that it can be called by external packages like myst_nb
    from myst_parser.config.main import MdParserConfig
    from myst_parser.parsers.sphinx_ import MystParser
    from myst_parser.sphinx_ext.directives import (
        FigureMarkdown,
        SubstitutionReferenceRole,
    )
    from myst_parser.sphinx_ext.mathjax import override_mathjax
    from myst_parser.sphinx_ext.references import (
        MystDomain,
        MystReferencesBuilder,
        MystRefrenceResolver,
    )

    if load_parser:
        app.add_source_suffix(".md", "markdown")
        app.add_source_parser(MystParser)

    app.add_role("sub-ref", SubstitutionReferenceRole())
    app.add_directive("figure-md", FigureMarkdown)

    app.add_domain(MystDomain)
    app.add_post_transform(MystRefrenceResolver)
    app.add_builder(MystReferencesBuilder)
    app.connect("env-check-consistency", load_project_inventory)

    for name, default, field in MdParserConfig().as_triple():
        if not field.metadata.get("docutils_only", False):
            # TODO add types?
            if field.metadata.get("deprecated"):
                app.add_config_value(f"myst_{name}", DEPRECATED, "env", types=Any)
            else:
                app.add_config_value(f"myst_{name}", default, "env", types=Any)

    app.connect("builder-inited", create_myst_config)
    app.connect("builder-inited", override_mathjax)


def create_myst_config(app):
    from sphinx.util import logging

    # Ignore type checkers because the attribute is dynamically assigned
    from sphinx.util.console import bold  # type: ignore[attr-defined]

    from myst_parser import __version__
    from myst_parser.config.main import MdParserConfig

    logger = logging.getLogger(__name__)

    values: Dict[str, Any] = {}

    for name, _, field in MdParserConfig().as_triple():
        if not field.metadata.get("docutils_only", False):
            if field.metadata.get("deprecated"):
                if app.config[f"myst_{name}"] != DEPRECATED:
                    logger.warning(
                        f"'myst_{name}' is deprecated, "
                        f"{field.metadata.get('deprecated')} "
                        f"[myst.{MystWarnings.DEPRECATED.value}]",
                        type="myst",
                        subtype=MystWarnings.DEPRECATED.value,
                    )
                continue
            values[name] = app.config[f"myst_{name}"]

    try:
        app.env.myst_config = MdParserConfig(**values)
        logger.info(bold("myst v%s:") + " %s", __version__, app.env.myst_config)
    except (TypeError, ValueError) as error:
        logger.error("myst configuration invalid: %s", error.args[0])
        app.env.myst_config = MdParserConfig()

    if "attrs_image" in app.env.myst_config.enable_extensions:
        logger.warning(
            "The `attrs_image` extension is deprecated, "
            "please use `attrs_inline` instead.",
            type="myst",
            subtype=MystWarnings.DEPRECATED.value,
        )


def load_project_inventory(_, env: BuildEnvironment):
    """Load the project inventory into the myst domain."""
    myst_domain: MystDomain = env.get_domain("myst")  # type: ignore
    myst_domain.update_project_inventory()
