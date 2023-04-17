import os
import shutil

import textwrap
import tempfile as compatible_tempfile
from pathlib import Path

from tests.utils import path_utils
from tests.utils.file_utils import makedirs


def create_file(file_path: str, indented_data=None) -> None:

  if isinstance(indented_data, bytes):
    # This is binary data rather than text.
    mode = "wb"
    data = indented_data
  else:
    mode = "w"
    data = textwrap.dedent(indented_data) if indented_data else indented_data
  with open(file_path, mode) as fi:
    if data:
      fi.write(data)


class Tempdir:
  """Context handler for creating temporary directories."""

  def __enter__(self):
    self.path = compatible_tempfile.mkdtemp()
    return self

  def create_directory(self, filename):
    """Create a subdirectory in the temporary directory."""
    path = path_utils.join(self.path, filename)
    makedirs(path)
    return path


  def delete_file(self, filename):
    os.unlink(path_utils.join(self.path, filename))

  def __exit__(self, error_type, value, tb):
    shutil.rmtree(path=self.path)
    return False  # reraise any exceptions

  def __getitem__(self, filename):
    """Get the full path for an entry in this directory."""
    return path_utils.join(self.path, filename)


