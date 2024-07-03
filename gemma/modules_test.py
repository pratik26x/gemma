# Copyright 2024 DeepMind Technologies Limited.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or  implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""Tests for transformer modules."""

import logging

from absl.testing import absltest
from gemma import modules
import jax
import jax.numpy as jnp
import numpy as np


_ATTN_TYPE = modules.AttentionType.GLOBAL


class EmbedderTest(absltest.TestCase):

  def test_encodes(self):
    vocab_size = 10
    embed_dim = 4
    embedder = modules.Embedder(vocab_size=vocab_size, embed_dim=embed_dim)
    output = embedder.apply(
        {'params': {'input_embedding': jnp.ones((vocab_size, embed_dim))}},
        [2, 3],
        method=modules.Embedder.encode,
    )
    expected = [[2.0, 2.0, 2.0, 2.0], [2.0, 2.0, 2.0, 2.0]]
    np.testing.assert_array_equal(output, jnp.array(expected))

  def test_decodes(self):
    vocab_size = 5
    embed_dim = 2
    embedder = modules.Embedder(vocab_size=vocab_size, embed_dim=embed_dim)
    output = embedder.apply(
        {'params': {'input_embedding': jnp.ones((vocab_size, embed_dim))}},
        jnp.array([1, 2]),
        method=modules.Embedder.decode,
    )
    expected = [3.0, 3.0, 3.0, 3.0, 3.0]
    np.testing.assert_array_equal(output, jnp.array(expected))


class AttentionTest(absltest.TestCase):

  def test_attention(self):
    num_heads = 2
    head_dim = 4
    features = 8
    segment_pos = 0
    cache_size = 3
    batch_size = 2
    attn_mask = jnp.ones((batch_size, 1, cache_size))
    attn = modules.Attention(
        num_heads=num_heads,
        num_kv_heads=num_heads,
        features=features,
        head_dim=head_dim,
        attn_type=_ATTN_TYPE,
    )
    cache = modules.Attention.init_cache(
        cache_size=cache_size,
        num_heads=num_heads,
        head_dim=head_dim,
        batch_size=batch_size,
        dtype=jnp.float32,
    )
    x = jnp.ones((batch_size, 1, features))
    params = attn.init(
        jax.random.PRNGKey(0),
        x,
        jnp.array([[segment_pos]]),
        cache,
        attn_mask,
    )
    cache, output = attn.apply(
        params, x, jnp.array([[segment_pos]]), cache, attn_mask
    )

    expected_cache_shape = (2, 3, 2, 4)
    expected_output_shape = (2, 1, 8)
    self.assertEqual(cache['k'].shape, expected_cache_shape)
    self.assertEqual(output.shape, expected_output_shape)

  def test_sliding_window(self):
    num_heads = 2
    head_dim = 4
    features = 8
    segment_pos = 0
    cache_size = 3
    batch_size = 2
    attn_mask = jnp.ones((batch_size, 1, cache_size))
    cache = modules.Attention.init_cache(
        cache_size=cache_size,
        num_heads=num_heads,
        head_dim=head_dim,
        batch_size=batch_size,
        dtype=jnp.float32,
    )
    x = jnp.ones((batch_size, 1, features))
    attn = modules.Attention(
        num_heads=num_heads,
        num_kv_heads=num_heads,
        features=features,
        head_dim=head_dim,
        attn_type=_ATTN_TYPE,
    )
    params = attn.init(
        jax.random.PRNGKey(0),
        x,
        jnp.array([[segment_pos]]),
        cache,
        attn_mask,
    )
    _, output = attn.apply(
        params, x, jnp.array([[segment_pos]]), cache, attn_mask
    )
    sliding_attn = modules.Attention(
        num_heads=num_heads,
        num_kv_heads=num_heads,
        features=features,
        head_dim=head_dim,
        attn_type=modules.AttentionType.LOCAL_SLIDING,
        sliding_window_size=2,
    )
    _, sliding_output = sliding_attn.apply(
        params, x, jnp.array([[segment_pos]]), cache, attn_mask
    )

    self.assertFalse((output == sliding_output).all())


class FeedForwardTest(absltest.TestCase):

  def test_ffw(self):
    features = 2
    hidden_dim = 3
    batch_size = 2
    inputs = jnp.arange(1, batch_size + 1)[:, None, None]
    inputs = jnp.repeat(inputs, features, axis=-1)
    ffw = modules.FeedForward(features=features, hidden_dim=hidden_dim)
    params = {
        'gating_einsum': jnp.ones((batch_size, features, hidden_dim)),
        'linear': jnp.ones((hidden_dim, features)),
    }

    outputs = ffw.apply({'params': params}, inputs)

    expected_val = [11.72758674, 47.99916]
    expected_shape = (2, 1, 2)
    np.testing.assert_array_almost_equal(outputs[:, 0, 0], expected_val)
    self.assertEqual(outputs.shape, expected_shape)


class BlockTest(absltest.TestCase):

  def test_block(self):
    num_heads = 2
    embed_dim = 4
    head_dim = 6
    cache_size = 3
    batch_size = 2
    inputs = jnp.ones((batch_size, 1, embed_dim))
    cache = modules.Attention.init_cache(
        cache_size=cache_size,
        num_heads=num_heads,
        head_dim=head_dim,
        batch_size=batch_size,
        dtype=jnp.float32,
    )
    attn_mask = jnp.ones((batch_size, 1, cache_size))
    block = modules.Block(
        num_heads=num_heads,
        num_kv_heads=num_heads,
        embed_dim=embed_dim,
        head_dim=head_dim,
        hidden_dim=1,
        use_post_attn_norm=False,
        use_post_ffw_norm=False,
        attn_type=_ATTN_TYPE,
    )
    params = block.init(
        jax.random.PRNGKey(0), inputs, jnp.array([[0]]), cache, attn_mask
    )

    new_cache, outputs = block.apply(
        params, inputs, jnp.array([[0]]), cache, attn_mask
    )

    expected_cache_shape = (2, 3, 2, 6)
    expected_output_shape = (2, 1, 4)
    self.assertEqual(new_cache['k'].shape, expected_cache_shape)
    self.assertEqual(outputs.shape, expected_output_shape)

  def test_post_attention_norm_modifies_output(self):
    num_heads = 1
    embed_dim = 1
    head_dim = 2
    hidden_dim = 1
    cache_size = 1
    batch_size = 1
    inputs = jnp.ones((batch_size, 1, embed_dim))
    cache = modules.Attention.init_cache(
        cache_size=cache_size,
        num_heads=num_heads,
        head_dim=head_dim,
        batch_size=batch_size,
        dtype=jnp.float32,
    )
    attn_mask = jnp.ones((batch_size, 1, cache_size))
    normed_block = modules.Block(
        num_heads=num_heads,
        num_kv_heads=num_heads,
        embed_dim=embed_dim,
        head_dim=head_dim,
        hidden_dim=hidden_dim,
        use_post_attn_norm=True,
        use_post_ffw_norm=False,
        attn_type=_ATTN_TYPE,
    )
    unnormed_block = modules.Block(
        num_heads=num_heads,
        num_kv_heads=num_heads,
        embed_dim=embed_dim,
        head_dim=head_dim,
        hidden_dim=hidden_dim,
        use_post_attn_norm=False,
        use_post_ffw_norm=False,
        attn_type=_ATTN_TYPE,
    )

    all_outputs = []
    for block in (normed_block, unnormed_block):
      params = block.init(
          jax.random.PRNGKey(0), inputs, jnp.array([[0]]), cache, attn_mask
      )

      _, outputs = block.apply(
          params, inputs, jnp.array([[0]]), cache, attn_mask
      )
      all_outputs.append(outputs)

    normed_output, unnormed_output = all_outputs  # pylint: disable=unbalanced-tuple-unpacking
    logging.info('normed_output: %s', normed_output)
    logging.info('unnormed_output: %s', unnormed_output)
    np.testing.assert_raises(
        AssertionError,
        np.testing.assert_array_equal,
        normed_output,
        unnormed_output,
    )

  def test_post_ffw_norm_preserves_output(self):
    num_heads = 1
    embed_dim = 1
    head_dim = 2
    hidden_dim = 1
    cache_size = 1
    batch_size = 1
    inputs = jnp.ones((batch_size, 1, embed_dim))
    cache = modules.Attention.init_cache(
        cache_size=cache_size,
        num_heads=num_heads,
        head_dim=head_dim,
        batch_size=batch_size,
        dtype=jnp.float32,
    )
    attn_mask = jnp.ones((batch_size, 1, cache_size))
    normed_block = modules.Block(
        num_heads=num_heads,
        num_kv_heads=num_heads,
        embed_dim=embed_dim,
        head_dim=head_dim,
        hidden_dim=hidden_dim,
        use_post_attn_norm=False,
        use_post_ffw_norm=True,
        attn_type=_ATTN_TYPE,
    )
    unnormed_block = modules.Block(
        num_heads=num_heads,
        num_kv_heads=num_heads,
        embed_dim=embed_dim,
        head_dim=head_dim,
        hidden_dim=hidden_dim,
        use_post_attn_norm=False,
        use_post_ffw_norm=False,
        attn_type=_ATTN_TYPE,
    )

    all_outputs = []
    for block in (normed_block, unnormed_block):
      params = block.init(
          jax.random.PRNGKey(0), inputs, jnp.array([[0]]), cache, attn_mask
      )

      _, outputs = block.apply(
          params, inputs, jnp.array([[0]]), cache, attn_mask
      )
      all_outputs.append(outputs)

    normed_output, unnormed_output = all_outputs  # pylint: disable=unbalanced-tuple-unpacking
    logging.info('normed_output: %s', normed_output)
    logging.info('unnormed_output: %s', unnormed_output)
    # TODO(b/350763078): Fix bug in the attention implementation. Normed and
    # unnormed outputs should not be equal.
    np.testing.assert_array_equal(normed_output, unnormed_output)


if __name__ == '__main__':
  absltest.main()
