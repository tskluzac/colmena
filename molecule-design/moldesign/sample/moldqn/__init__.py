import logging
from typing import Callable, Set

from rdkit import RDLogger

from .agents.dqn_variable_actions import DQNFinalState
from .envs import Molecule

# Set up the logger
logger = logging.getLogger(__name__)
rdkit_logger = RDLogger.logger()
rdkit_logger.setLevel(RDLogger.CRITICAL)


def generate_molecules(target_fn: Callable[[str], float], episodes: int = 10,
                       n_steps: int = 32, update_q_every: int = 10) -> Set[str]:
    """Perform the RL experiment

    Args:
        target_fn (Callable): Function to be optimized
        env (Molecule): Molecular environment used to model the system
        episodes (int): Number of episodes to run
        n_steps (int): Maximum number of steps per episode
        update_q_every (int): After how many updates to update the Q function
    Returns:
        ([str]) List of molecules that were created
    """

    # Make the environment
    env = Molecule(max_steps=n_steps, target_fn=target_fn)

    # Run the reinforcement learning
    best_reward = 0

    # Prepare the output
    output = set()

    # Make the agent
    agent = DQNFinalState(env, epsilon=1.0)

    # Keep track of the smiles strings
    for e in range(episodes):
        current_state = env.reset()
        for s in range(n_steps):
            # Get action based on current state
            action = agent.action()

            # Fix cluster action
            new_state, reward, done, _ = env.step(action)

            # Check if it's the last step and flag as done
            if s == n_steps:
                logger.debug('Last step  ... done')
                done = True

            # Add the state to the output
            output.add(env.state)

            # Save outcome
            agent.remember(current_state, action, reward,
                           new_state, agent.env.action_space.get_possible_actions(), done)

            # Train model
            agent.train()

            # Update state
            current_state = new_state

            if best_reward > reward:
                best_reward = reward
                logger.info("Best reward: %s" % best_reward)

            if done:
                break

        # Update the Q network after certain numbers of episodes and adjust epsilon
        if e > 0 and e % update_q_every == 0:
            agent.update_target_q_network()
        agent.epsilon_adj()

    return output