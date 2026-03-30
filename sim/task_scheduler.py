from __future__ import annotations

from dataclasses import dataclass


TASK_MODES = ("rest", "trot")
TASK_PARAM_ALIASES = {
    "vx": "vx",
    "x_vel": "vx",
    "vy": "vy",
    "y_vel": "vy",
    "yaw": "yaw_rate",
    "yaw_rate": "yaw_rate",
    "wz": "yaw_rate",
    "height": "height",
    "z": "height",
    "pitch": "pitch",
    "roll": "roll",
    "z_clearance": "z_clearance",
    "clearance": "z_clearance",
    "overlap_time": "overlap_time",
    "overlap": "overlap_time",
    "swing_time": "swing_time",
    "swing": "swing_time",
    "attitude_kp": "attitude_kp",
    "att_kp": "attitude_kp",
    "attitude_kd": "attitude_kd",
    "att_kd": "attitude_kd",
    "velocity_kp": "velocity_kp",
    "vel_kp": "velocity_kp",
    "transition_time": "transition_time",
    "transition": "transition_time",
    "blend_time": "transition_time",
    "blend": "transition_time",
}
TASK_PARAM_RENDER_ORDER = (
    "vx",
    "vy",
    "yaw_rate",
    "height",
    "pitch",
    "roll",
    "z_clearance",
    "overlap_time",
    "swing_time",
    "attitude_kp",
    "attitude_kd",
    "velocity_kp",
    "transition_time",
)


@dataclass(frozen=True)
class TaskStep:
    """One scheduled task segment."""

    mode: str
    duration: float | None = None
    params: dict[str, float] | None = None
    transition_time: float | None = None


class TaskScheduler:
    """High-level task scheduler for simulated command sequencing."""

    def __init__(
        self,
        steps: list[TaskStep],
        activation_delay: float = 0.0,
        default_transition_time: float = 0.0,
    ):
        if not steps:
            raise ValueError("TaskScheduler requires at least one task step.")
        self.activation_delay = max(0.0, float(activation_delay))
        self.default_transition_time = max(0.0, float(default_transition_time))
        self.steps = [self._validate_step(step) for step in steps]

    @classmethod
    def from_args(cls, args) -> "TaskScheduler":
        if args.task_sequence:
            steps = cls.parse_sequence(args.task_sequence)
        else:
            steps = cls.default_sequence(args.mode, args.settle)
        return cls(
            steps,
            activation_delay=args.activation_delay,
            default_transition_time=args.transition_time,
        )

    @staticmethod
    def default_sequence(mode: str, settle: float) -> list[TaskStep]:
        if mode == "rest":
            return [TaskStep("rest")]
        if settle > 0.0:
            return [TaskStep("rest", duration=settle), TaskStep("trot")]
        return [TaskStep("trot")]

    @staticmethod
    def parse_sequence(sequence_text: str) -> list[TaskStep]:
        steps: list[TaskStep] = []
        tokens = [token.strip() for token in sequence_text.split(",") if token.strip()]
        if not tokens:
            raise ValueError("`task_sequence` is empty.")

        for index, token in enumerate(tokens):
            step_text, param_text = TaskScheduler._split_token(token)
            parts = [part.strip() for part in step_text.split(":")]
            if len(parts) > 2:
                raise ValueError(f"Invalid task token `{token}`.")

            mode = parts[0].lower()
            if mode not in TASK_MODES:
                raise ValueError(f"Unsupported task mode `{mode}`.")

            duration: float | None = None
            if len(parts) == 2 and parts[1]:
                duration_text = parts[1].lower()
                if duration_text in ("inf", "forever"):
                    duration = None
                else:
                    duration = float(duration_text)
            elif len(parts) == 1 and index < len(tokens) - 1:
                raise ValueError(
                    "Only the last task step may omit duration. "
                    "Example: `rest:1.0,trot:2.0,rest`."
                )

            params = TaskScheduler._parse_params(param_text)
            transition_time = params.pop("transition_time", None)
            steps.append(
                TaskStep(
                    mode=mode,
                    duration=duration,
                    params=params,
                    transition_time=transition_time,
                )
            )
        return steps

    def _validate_step(self, step: TaskStep) -> TaskStep:
        mode = step.mode.lower()
        if mode not in TASK_MODES:
            raise ValueError(f"Unsupported task mode `{mode}`.")
        if step.duration is not None and step.duration < 0.0:
            raise ValueError("Task duration must be non-negative.")
        params = dict(step.params or {})
        for key, value in params.items():
            if key not in TASK_PARAM_ALIASES.values():
                raise ValueError(f"Unsupported task parameter `{key}`.")
            params[key] = float(value)
        transition_time = self.default_transition_time if step.transition_time is None else float(step.transition_time)
        if transition_time < 0.0:
            raise ValueError("Task transition_time must be non-negative.")
        return TaskStep(
            mode=mode,
            duration=step.duration,
            params=params,
            transition_time=transition_time,
        )

    @staticmethod
    def _split_token(token: str) -> tuple[str, str | None]:
        if "@" not in token:
            return token, None
        step_text, param_text = token.split("@", 1)
        return step_text.strip(), param_text.strip()

    @staticmethod
    def _parse_params(param_text: str | None) -> dict[str, float]:
        if not param_text:
            return {}

        params: dict[str, float] = {}
        assignments = [item.strip() for item in param_text.replace("|", ";").split(";") if item.strip()]
        if not assignments:
            raise ValueError("Task parameter list is empty after `@`.")

        for assignment in assignments:
            if "=" not in assignment:
                raise ValueError(f"Invalid task parameter `{assignment}`.")
            raw_key, raw_value = assignment.split("=", 1)
            key = raw_key.strip().lower()
            value = raw_value.strip()
            if key not in TASK_PARAM_ALIASES:
                raise ValueError(f"Unsupported task parameter `{raw_key}`.")
            params[TASK_PARAM_ALIASES[key]] = float(value)
        return params

    def is_waiting(self, sim_time: float) -> bool:
        return sim_time < self.activation_delay

    def step_at(self, sim_time: float) -> TaskStep:
        return self.step_info_at(sim_time)[1]

    def step_info_at(self, sim_time: float) -> tuple[int, TaskStep]:
        if self.is_waiting(sim_time):
            raise ValueError("Task mode is undefined before activation.")

        remaining_time = sim_time - self.activation_delay
        for step_index, step in enumerate(self.steps):
            if step.duration is None or remaining_time < step.duration:
                return step_index, step
            remaining_time -= step.duration
        return len(self.steps) - 1, self.steps[-1]

    def step_elapsed_at(self, sim_time: float) -> tuple[int, TaskStep, float]:
        if self.is_waiting(sim_time):
            raise ValueError("Task mode is undefined before activation.")

        remaining_time = sim_time - self.activation_delay
        for step_index, step in enumerate(self.steps):
            if step.duration is None or remaining_time < step.duration:
                return step_index, step, remaining_time
            remaining_time -= step.duration
        return len(self.steps) - 1, self.steps[-1], remaining_time

    def transition_info_at(self, sim_time: float) -> tuple[int, TaskStep | None, TaskStep, float]:
        step_index, step, step_elapsed = self.step_elapsed_at(sim_time)
        previous_step = self.steps[step_index - 1] if step_index > 0 else None
        transition_time = step.transition_time or 0.0
        if step.duration is not None:
            transition_time = min(transition_time, step.duration)
        if transition_time <= 0.0:
            alpha = 1.0
        else:
            alpha = min(1.0, max(0.0, step_elapsed / transition_time))
        return step_index, previous_step, step, alpha

    def mode_at(self, sim_time: float) -> str:
        return self.step_at(sim_time).mode

    def render_step(self, step: TaskStep) -> str:
        rendered_step = step.mode if step.duration is None else f"{step.mode}:{step.duration:g}"
        rendered_params = []
        if step.params:
            rendered_params = [
                f"{key}={step.params[key]:g}"
                for key in TASK_PARAM_RENDER_ORDER
                if key in step.params
            ]
        if (step.transition_time or 0.0) > 0.0:
            rendered_params.append(f"transition_time={step.transition_time:g}")
        if rendered_params:
            rendered_step = f"{rendered_step}@{';'.join(rendered_params)}"
        return rendered_step

    def sequence_text(self) -> str:
        return " -> ".join(self.render_step(step) for step in self.steps)
