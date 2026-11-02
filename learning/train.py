"""Training entry point disabled until real, timestamped outcome labels exist."""


def simulate_training_session(epochs=50):
    raise RuntimeError(
        "Synthetic training is disabled. Supply verified historical signal outcomes before training."
    )


if __name__ == "__main__":
    simulate_training_session()
