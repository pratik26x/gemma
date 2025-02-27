# Copyright 2024 DeepMind Technologies Limited.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Text processing utilities."""


from etils import epy as _epy

# pylint: disable=g-import-not-at-top,g-importing-member

with _epy.lazy_api_imports(globals()):
  from gemma.gm.text._tokenizer import Gemma2Tokenizer
  from gemma.gm.text._tokenizer import Tokenizer
  from gemma.gm.text._sampler import Sampler

  # Sampling methods
  # TODO(epot): Add `TopK`,...
  from gemma.gm.text._sampling import SamplingMethod
  from gemma.gm.text._sampling import Greedy
  from gemma.gm.text._sampling import RandomSampling
