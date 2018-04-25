# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Original work Copyright (c) 2018 Mozilla Corporation
# Modified work Copyright (c) 2018 NVIDIA Corporation

from __future__ import absolute_import, division, print_function
import tensorflow as tf

from .loss import Loss
from open_seq2seq.utils.utils import mask_nans, deco_print


def dense_to_sparse(dense_tensor, sequence_length):
  indices = tf.where(tf.sequence_mask(sequence_length))
  values = tf.gather_nd(dense_tensor, indices)
  shape = tf.shape(dense_tensor, out_type=tf.int64)
  return tf.SparseTensor(indices, values, shape)


class CTCLoss(Loss):
  """Implementation of the CTC loss."""
  @staticmethod
  def get_optional_params():
    return dict(Loss.get_optional_params(), **{
      'mask_nan': bool,
    })

  def __init__(self, params, model, name="ctc_loss"):
    super(CTCLoss, self).__init__(params, model, name)
    self._mask_nan = self.params.get("mask_nan", True)
    # this loss can only operate in full precision
    if self.params['dtype'] != tf.float32:
      deco_print("Warning: defaulting CTC loss to work in float32")
    self.params['dtype'] = tf.float32

  def _compute_loss(self, input_dict):
    """
    Computes CTC loss
    :param input_dict: inputs to compute loss
    {
          "logits": logits tensor of shape [batch_size, T, dim]
          "target_sequence": tensor of shape [batch_size, T]
          "src_lengths": tensor of shape [batch_size]
          "tgt_lengths": tensor of shape [batch_size]
    }
    :return: Singleton loss tensor
    """
    logits = input_dict['decoder_output']['logits']
    tgt_sequence = input_dict['tgt_sequence']
    tgt_length = input_dict['tgt_length']
    # this loss needs an access to src_length since they
    # might get changed in the encoder
    src_length = input_dict['decoder_output']['src_length']

    # Compute the CTC loss
    total_loss = tf.nn.ctc_loss(
      labels=dense_to_sparse(tgt_sequence, tgt_length),
      inputs=logits,
      sequence_length=src_length,
      ignore_longer_outputs_than_inputs=True,
    )

    if self._mask_nan:
      total_loss = mask_nans(total_loss)

    # Calculate the average loss across the batch
    avg_loss = tf.reduce_mean(total_loss)
    return avg_loss
