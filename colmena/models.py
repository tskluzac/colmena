import pickle as pkl
from datetime import datetime
from typing import Any, Tuple, Dict, Optional, Union

from pydantic import BaseModel, Field


class Result(BaseModel):
    """A class which describes the inputs and results of the calculations evaluated by the MethodServer

    Each instance of this class stores the inputs and outputs to the function along with some tracking
    information allowing for performance analysis (e.g., time submitted to Queue, time received by client).
    All times are listed as UTC Unix timestamps.

    The Result class also handles serialization of the data to be transmitted over a RedisQueue
    """

    inputs: Union[Tuple[Tuple[Any, ...], Dict[str, Any]], str] =\
        Field(None, description="Input to a function. Positional and keyword arguments. The `str` data type "
                                "is for advanced usage and is used to communicate serialized objects.")
    value: Any = Field(None, description="Output of a function")
    method: Optional[str] = Field(None, description="Name of the method to run.")
    success: Optional[bool] = Field(None, description="Whether the task completed successfully")

    time_created: float = Field(None, description="Time this value object was created")
    time_input_received: float = Field(None, description="Time the inputs was received by the method server")
    time_compute_started: float = Field(None, description="Time workflow process began executing a task")
    time_result_sent: float = Field(None, description="Time message was sent from the server")
    time_running: float = Field(None, description="Runtime of the method, if available")
    time_result_received: float = Field(None, description="Time value was received by client")

    def __init__(self, inputs: Tuple[Tuple[Any], Dict[str, Any]], **kwargs):
        """
        Args:
             inputs (Any, Dict): Inputs to a function. Separated into positional and keyword arguments
        """
        super().__init__(inputs=inputs, **kwargs)

        # Mark "created" only if the value is not already set
        if 'time_created' not in kwargs:
            self.time_created = datetime.utcnow().timestamp()

    @property
    def args(self) -> Tuple[Any]:
        return self.inputs[0]

    @property
    def kwargs(self) -> Dict[str, Any]:
        return self.inputs[1]

    def mark_result_received(self):
        """Mark that a completed computation was received by a client"""
        self.time_result_received = datetime.utcnow().timestamp()

    def mark_input_received(self):
        """Mark that a method server has received a value"""
        self.time_input_received = datetime.utcnow().timestamp()

    def set_result(self, result: Any, runtime: float = None):
        """Set the value of this computation

        Automatically sets the "time_result_completed" field
        and, if known, defines the runtime.

        Args:
            result: Result to be stored
            runtime (float): Runtime for the function
        """
        self.value = result
        self.time_result_sent = datetime.utcnow().timestamp()
        self.time_running = runtime
        self.success = True

    def pickle_data(self):
        """Stores the input and value fields as a pickled objects"""
        # TODO (wardlt): Talk to Yadu and co about best practices for pickling
        _value = self.value
        _inputs = self.inputs
        try:
            self.inputs = pkl.dumps(_inputs).hex()
            self.value = pkl.dumps(_value).hex()
        except pkl.PickleError as e:
            # Put the original values back
            self.inputs = _inputs
            self.value = _value
            raise e

    def unpickle_data(self):
        """Convert data out of pickled form"""
        # Check that the data is actually a string
        if not (isinstance(self.value, str) and isinstance(self.inputs, str)):
            raise ValueError('Data is not in a serialized form. Are you sure you need to unpickle?')

        # Deserialize the data
        _value = self.value
        _inputs = self.inputs
        try:
            self.inputs = pkl.loads(bytes.fromhex(_inputs))
            self.value = pkl.loads(bytes.fromhex(_value))
        except pkl.PickleError:
            # Put the original values back
            self.inputs = _inputs
            self.value = _value
