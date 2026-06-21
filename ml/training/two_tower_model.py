"""Build Two-Tower retrieval model with TensorFlow/Keras."""

from __future__ import annotations

import tensorflow as tf


def build_two_tower_model(
    *,
    user_vocab_size: int,
    item_vocab_size: int,
    embedding_dim: int = 64,
) -> tf.keras.Model:
    user_input = tf.keras.Input(shape=(), dtype=tf.int32, name="user_id")
    item_input = tf.keras.Input(shape=(), dtype=tf.int32, name="item_id")

    user_vector = tf.keras.layers.Embedding(
        input_dim=user_vocab_size,
        output_dim=embedding_dim,
        name="user_embedding",
    )(user_input)
    item_vector = tf.keras.layers.Embedding(
        input_dim=item_vocab_size,
        output_dim=embedding_dim,
        name="item_embedding",
    )(item_input)

    user_vector = tf.keras.layers.Flatten()(user_vector)
    item_vector = tf.keras.layers.Flatten()(item_vector)

    user_vector = tf.keras.layers.UnitNormalization()(user_vector)
    item_vector = tf.keras.layers.UnitNormalization()(item_vector)

    dot = tf.keras.layers.Dot(axes=1, normalize=False)([user_vector, item_vector])
    output = tf.keras.layers.Activation("sigmoid", name="score")(dot)

    model = tf.keras.Model(inputs=[user_input, item_input], outputs=output, name="two_tower")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(),
        loss="binary_crossentropy",
        metrics=[tf.keras.metrics.AUC(name="auc")],
    )
    return model


def extract_item_embeddings(model: tf.keras.Model) -> tf.keras.layers.Embedding:
    return model.get_layer("item_embedding")
