import numpy as np
from resco_benchmark.agents.agent import Agent, IndependentAgent
from resco_benchmark.config.config import config as cfg


class MAXWAVE(IndependentAgent):
    def __init__(self, obs_act):
        super().__init__(obs_act)
        for agent_id in obs_act:
            self.agents[agent_id] = WaveAgent(agent_id)


class WaveAgent(Agent):
    def __init__(self, agent_id=None):
        super().__init__()
        self.agent_id = agent_id

    def act(self, observation):
        all_press = []
        for pair in cfg["phase_pairs"]:
            left = cfg.directions[pair[0]]
            right = cfg.directions[pair[1]]
            all_press.append(observation[left] + observation[right])

        if cfg.pair_to_act_map is not None and self.agent_id in cfg.pair_to_act_map:
            act_map = cfg.pair_to_act_map[self.agent_id]
            best_act = None
            best_press = -float("inf")
            for pair_idx, act in act_map.items():
                if all_press[pair_idx] > best_press:
                    best_press = all_press[pair_idx]
                    best_act = act
            return best_act

        return np.argmax(all_press)

    def observe(self, observation, reward, done, info):
        pass
