"""
Handles reading of different event/waveform containing files
"""
from abc import abstractmethod
from os.path import exists
from traitlets import Unicode, Int, Set
from ctapipe.core import Component
from ctapipe.core import Provenance

__all__ = ['EventSource', ]


class EventSource(Component):
    """
    Parent class for EventFileReaders of different sources.

    A new EventFileReader should be created for each type of event file read
    into ctapipe, e.g. sim_telarray files are read by the `HESSIOEventSource`.

    EventFileReader provides a common high-level interface for accessing event
    information from different data sources (simulation or different camera
    file formats). Creating an EventFileReader for a new
    file format ensures that data can be accessed in a common way,
    irregardless of the file format.

    EventFileReader itself is an abstract class. To use an EventFileReader you
    must use a subclass that is relevant for the file format you
    are reading (for example you must use
    `ctapipe.io.hessiofilereader.HESSIOEventSource` to read a hessio format
    file). Alternatively you can use
    `ctapipe.io.eventfilereader.EventSourceFactory` to automatically
    select the correct EventFileReader subclass for the file format you wish
    to read.

    To create an instance of an EventFileReader you must pass the traitlet
    configuration (containing the input_url) and the
    `ctapipe.core.tool.Tool`. Therefore from inside a Tool you would do:

    >>> event_source = EventSource(self.config, self)

    An example of how to use `ctapipe.core.tool.Tool` and
    `ctapipe.io.eventfilereader.EventSourceFactory` can be found in
    ctapipe/examples/calibration_pipeline.py.

    However if you are not inside a Tool, you can still create an instance and
    supply an input_url via:

    >>> event_source = EventSource( input_url="/path/to/file")

    To loop through the events in a file:

    >>> event_source = EventSource( input_url="/path/to/file")
    >>> for event in event_source:
    >>>    print(event.count)

    **NOTE**: Every time a new loop is started through the event_source, it restarts
    from the first event.

    Alternatively one can use EventFileReader in a `with` statement to ensure
    the correct cleanups are performed when you are finished with the event_source:

    >>> with EventSource( input_url="/path/to/file") as event_source:
    >>>    for event in event_source:
    >>>       print(event.count)

    **NOTE**: The "event" that is returned from the generator is a pointer.
    Any operation that progresses that instance of the generator further will
    change the data pointed to by "event". If you wish to ensure a particular
    event is kept, you should perform a `event_copy = copy.deepcopy(event)`.


    Attributes
    ----------
    input_url : str
        Path to the input event file.
    max_events : int
        Maximum number of events to loop through in generator
    metadata : dict
        A dictionary containing the metadata of the file. This could include:
        * is_simulation (bool indicating if the file contains simulated events)
        * Telescope:Camera names (list if file contains multiple)
        * Information in the file header
        * Observation ID
    """

    input_url = Unicode(
        '',
        help='Path to the input file containing events.'
    ).tag(config=True)
    max_events = Int(
        None,
        allow_none=True,
        help='Maximum number of events that will be read from the file'
    ).tag(config=True)

    allowed_tels = Set(
        help=('list of allowed tel_ids, others will be ignored. '
              'If left empty, all telescopes in the input stream '
              'will be included')
    ).tag(config=True)


    def __init__(self, config=None, tool=None, **kwargs):
        """
        Class to handle generic input files. Enables obtaining the "source"
        generator, regardless of the type of file (either hessio or camera
        file).

        Parameters
        ----------
        config : traitlets.loader.Config
            Configuration specified by config file or cmdline arguments.
            Used to set traitlet values.
            Set to None if no configuration to pass.
        tool : ctapipe.core.Tool
            Tool executable that is calling this component.
            Passes the correct logger to the component.
            Set to None if no Tool to pass.
        kwargs
        """
        super().__init__(config=config, parent=tool, **kwargs)

        self.metadata = dict(is_simulation=False)

        if not exists(self.input_url):
            raise FileNotFoundError("file path does not exist: '{}'"
                                    .format(self.input_url))
        self.log.info("INPUT PATH = {}".format(self.input_url))

        if self.max_events:
            self.log.info("Max events being read = {}".format(self.max_events))

        Provenance().add_input_file(self.input_url, role='dl0.sub.evt')

    @staticmethod
    @abstractmethod
    def is_compatible(file_path):
        """
        Abstract method to be defined in child class.

        Perform a set of checks to see if the input file is compatible
        with this file event_source.

        Parameters
        ----------
        file_path : str
            File path to the event file.

        Returns
        -------
        compatible : bool
            True if file is compatible, False if it is incompatible
        """

    @property
    def is_stream(self):
        """
        Bool indicating if input is a stream. If it is then it is incompatible
        with `ctapipe.io.eventseeker.EventSeeker`.

        TODO: Define a method to detect if it is a stream

        Returns
        -------
        bool
            If True, then input is a stream.
        """
        return False

    @abstractmethod
    def _generator(self):
        """
        Abstract method to be defined in child class.

        Generator where the filling of the `ctapipe.io.containers` occurs.

        Returns
        -------
        generator
        """

    def __iter__(self):
        """
        Generator that iterates through `_generator`, but keeps track of
        `self.max_events`.

        Returns
        -------
        generator
        """
        for event in self._generator():
            if self.max_events and event.count >= self.max_events:
                break
            yield event

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
