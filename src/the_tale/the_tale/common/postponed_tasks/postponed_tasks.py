
import smart_imports

smart_imports.all()


class FakePostponedInternalTask(PostponedLogic):

    TYPE = 'fake-task'
    INITIAL_STATE = 666

    def __init__(self, state=888, result_state=POSTPONED_TASK_LOGIC_RESULT.SUCCESS):
        self.state = state
        self.result_state = result_state

    def process(self, main_task):
        return self.result_state

    def serialize(self): return {'state': self.state,
                                 'result_state': self.result_state}

    @property
    def processed_data(self): return {'test_value': 666}

    @property
    def error_message(self): return 'some error message'
