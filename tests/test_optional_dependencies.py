"""Tests that the file-datasource dependencies ([files] extra) stay optional."""

import subprocess
import sys

import pytest

from etter.datasources import IGNBDCartoSource, SwissBoundaries3DSource, SwissNames3DSource, geo_dataframe_source


def test_import_etter_does_not_load_file_datasource_dependencies():
    code = (
        "import sys, etter, etter.datasources.swissnames3d, etter.datasources.swissboundaries3d, "
        "etter.datasources.ign_bdcarto, etter.datasources.geo_dataframe_source; "
        "print(sorted(m for m in ('geopandas', 'pandas', 'rapidfuzz') if m in sys.modules))"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "[]"


@pytest.mark.parametrize("source_class", [SwissNames3DSource, SwissBoundaries3DSource, IGNBDCartoSource])
@pytest.mark.parametrize("missing", ["geopandas", "rapidfuzz"])
def test_file_datasource_without_files_extra_names_the_extra(monkeypatch, tmp_path, source_class, missing):
    real_find_spec = geo_dataframe_source.find_spec
    monkeypatch.setattr(
        geo_dataframe_source, "find_spec", lambda name: None if name == missing else real_find_spec(name)
    )
    with pytest.raises(ImportError, match=rf"require {missing}\..*etter\[files\]"):
        source_class(tmp_path)
