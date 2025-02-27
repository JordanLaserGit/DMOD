from .message import AbstractInitRequest, MessageEventType, Response
from dmod.core.serializable import Serializable
from .maas_request import ExternalRequest, ExternalRequestResponse
from dmod.core.meta_data import DataCategory, DataDomain, DataFormat, DataRequirement
from numbers import Number
from enum import Enum
from typing import Dict, Optional, Union, List


class QueryType(Enum):
    LIST_FILES = 1
    GET_CATEGORY = 2
    GET_FORMAT = 3
    GET_INDICES = 4
    GET_DATA_FIELDS = 5
    GET_VALUES = 6
    GET_MIN_VALUE = 7
    GET_MAX_VALUE = 8

    @classmethod
    def get_for_name(cls, name_str: str) -> 'QueryType':
        """
        Get the enum value corresponding to the given string, ignoring case, and defaulting to ``LIST_FILES``.

        Parameters
        ----------
        name_str : str
            Expected string representation of one of the enum values.

        Returns
        -------
        QueryType
            Enum value corresponding to the given string, or ``LIST_FILES`` if correspondence could not be determined.
        """
        cleaned_up_str = name_str.strip().upper()
        for value in cls:
            if value.name.upper() == cleaned_up_str:
                return value
        return cls.LIST_FILES


class DatasetQuery(Serializable):

    _KEY_QUERY_TYPE = 'query_type'

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict) -> Optional['DatasetQuery']:
        try:
            return cls(query_type=QueryType.get_for_name(json_obj[cls._KEY_QUERY_TYPE]))
        except Exception as e:
            return None

    def __hash__(self):
        return hash(self.query_type)

    def __eq__(self, other):
        return isinstance(other, DatasetQuery) and self.query_type == other.query_type

    def __init__(self, query_type: QueryType):
        self.query_type = query_type

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        serial = dict()
        serial[self._KEY_QUERY_TYPE] = self.query_type.name
        return serial


class ManagementAction(Enum):
    """
    Type enumerating the standard actions that can be requested via ::class:`DatasetManagementMessage`.
    """
    UNKNOWN = (-1, False, False)
    """ Placeholder action for when actual action is not known, generally representing an error (e.g., bad parsing). """
    CREATE = (1, True, True, True)
    """ Dataset creation action. """
    ADD_DATA = (2, True, False)
    """ Addition of data to an existing dataset. """
    REMOVE_DATA = (3, True, False)
    """ Removal of data from an existing dataset. """
    DELETE = (4, True, False)
    """ Deletion of an existing dataset. """
    SEARCH = (5, False, True)
    """ Search for dataset(s) satisfying certain conditions (e.g., AORC forcings for right times and catchments). """
    QUERY = (6, True, False)
    """ Query for information about a dataset (e.g., what time period and catchments does a forcing dataset cover). """
    CLOSE_AWAITING = (7, False, False)
    """ Action to close an ongoing, multi-message dialog. """
    LIST_ALL = (8, False, False)
    """ Like ``SEARCH``, but just list all datasets. """
    REQUEST_DATA = (9, True, False)
    """ Action to request data from a dataset, which expect a response with details on how. """

    @classmethod
    def get_for_name(cls, name_str: str) -> 'ManagementAction':
        """
        Get the enum value corresponding to the given string, ignoring case, and defaulting to ``UNKNOWN``.

        Parameters
        ----------
        name_str : str
            Expected string representation of one of the enum values.

        Returns
        -------
        ManagementAction
            Enum value corresponding to the given string, or ``UNKNOWN`` if correspondence could not be determined.
        """
        cleaned_up_str = name_str.strip().upper()
        for value in cls:
            if value.name.upper() == cleaned_up_str:
                return value
        return cls.UNKNOWN

    def __init__(self, uid: int, requires_name: bool, requires_category: bool, requires_domain: bool = False):
        self._uid = uid
        self._requires_name = requires_name
        self._requires_category = requires_category
        self._requires_domain = requires_domain

    @property
    def requires_data_category(self) -> bool:
        """
        Whether this type of action requires a data category in order for the action to be valid.

        Returns
        -------
        bool
            Whether this type of action requires a data category in order for the action to be valid.

        See Also
        -------
        ::method:`requires_dataset_name`
        """
        return self._requires_category

    @property
    def requires_data_domain(self) -> bool:
        """
        Whether this type of action requires a data domain in order for the action to be valid.

        Returns
        -------
        bool
            Whether this type of action requires a data domain in order for the action to be valid.

        See Also
        -------
        ::method:`requires_dataset_name`
        """
        return self._requires_category

    @property
    def requires_dataset_name(self) -> bool:
        """
        Whether this type of action requires a dataset name in order for the action to be valid.

        Certain actions - e.g., ``CREATE`` - cannot be performed without the name of the dataset involved. However,
        others, such as ``SEARCH``, inherently do not.

        This property provides a convenient way of accessing whether a name is required for a particular enum value's
        action to be performable.

        Returns
        -------
        bool
            Whether this type of action requires a dataset name in order for the action to be valid.
        """
        return self._requires_name


class DatasetManagementMessage(AbstractInitRequest):
    """
    Message type for initiating any action related to dataset management.

    Valid actions are enumerated by the ::class:`ManagementAction`.
    """

    event_type: MessageEventType = MessageEventType.DATASET_MANAGEMENT

    _SERIAL_KEY_ACTION = 'action'
    _SERIAL_KEY_CATEGORY = 'category'
    _SERIAL_KEY_DATA_DOMAIN = 'data_domain'
    _SERIAL_KEY_DATA_LOCATION = 'data_location'
    _SERIAL_KEY_DATASET_NAME = 'dataset_name'
    _SERIAL_KEY_IS_PENDING_DATA = 'pending_data'
    _SERIAL_KEY_QUERY = 'query'
    _SERIAL_KEY_IS_READ_ONLY = 'read_only'

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict) -> Optional['DatasetManagementMessage']:
        """
        Inflate serialized representation back to a full object, if serial representation is valid.

        Parameters
        ----------
        json_obj : dict
            Serialized representation of a ::class:`DatasetManagementMessage` instance.

        Returns
        -------
        Optional[DatasetManagementMessage]
            The inflated ::class:`DatasetManagementMessage`, or ``None`` if the serialized form was invalid.
        """
        try:
            # Grab the class to deserialize, popping it from the json obj (it was temp injected by a subclass) if there
            deserialized_class = json_obj.pop('deserialized_class', cls)

            # Similarly, get/pop any temporarily injected kwargs values to pass to deserialized_class's init function
            deserialized_class_kwargs = json_obj.pop('deserialized_class_kwargs', dict())

            action = ManagementAction.get_for_name(json_obj[cls._SERIAL_KEY_ACTION])
            if json_obj[cls._SERIAL_KEY_ACTION] != action.name:
                raise RuntimeError("Unparseable serialized {} value: {}".format(ManagementAction.__name__,
                                                                                json_obj[cls._SERIAL_KEY_ACTION]))

            dataset_name = json_obj.get(cls._SERIAL_KEY_DATASET_NAME)
            category_str = json_obj.get(cls._SERIAL_KEY_CATEGORY)
            category = None if category_str is None else DataCategory.get_for_name(category_str)
            data_loc = json_obj.get(cls._SERIAL_KEY_DATA_LOCATION)
            #page = json_obj[cls._SERIAL_KEY_PAGE] if cls._SERIAL_KEY_PAGE in json_obj else None
            if cls._SERIAL_KEY_QUERY in json_obj:
                query = DatasetQuery.factory_init_from_deserialized_json(json_obj[cls._SERIAL_KEY_QUERY])
            else:
                query = None
            if cls._SERIAL_KEY_DATA_DOMAIN in json_obj:
                domain = DataDomain.factory_init_from_deserialized_json(json_obj[cls._SERIAL_KEY_DATA_DOMAIN])
            else:
                domain = None

            return deserialized_class(action=action, dataset_name=dataset_name, category=category,
                                      is_read_only_dataset=json_obj[cls._SERIAL_KEY_IS_READ_ONLY], domain=domain,
                                      data_location=data_loc,
                                      is_pending_data=json_obj.get(cls._SERIAL_KEY_IS_PENDING_DATA), #page=page,
                                      query=query, **deserialized_class_kwargs)
        except Exception as e:
            return None

    def __eq__(self, other):
        try:
            if not isinstance(self, other.__class__):
                return False
            elif self.dataset_name != other.dataset_name or self.is_read_only_dataset != other.is_read_only_dataset:
                return False
            elif self.data_category != other.data_category:
                return False
            if self.data_domain != other.data_domain:
                return False
            elif self.is_pending_data != other.is_pending_data:
                return False
            elif self.query != other.query:
                return False
            else:
                return True
        except:
            return False

    def __hash__(self):
        return hash('-'.join([self.management_action.name, self.dataset_name, str(self.is_read_only_dataset),
                              self.data_category.name, str(hash(self.data_domain)), self.data_location,
                              str(self.is_pending_data), self.query.to_json()]))

    def __init__(self, action: ManagementAction, dataset_name: Optional[str] = None, is_read_only_dataset: bool = False,
                 category: Optional[DataCategory] = None, domain: Optional[DataDomain] = None,
                 data_location: Optional[str] = None, is_pending_data: bool = False,
                 query: Optional[DatasetQuery] = None, *args, **kwargs):
        """
        Initialize this instance.

        Parameters
        ----------
        action : ManagementAction
            The action this message embodies or requests.
        dataset_name : Optional[str]
            The optional name of the involved dataset, when applicable; defaults to ``None``.
        is_read_only_dataset : bool
            Whether dataset involved is, should be, or must be (depending on action) read-only; defaults to ``False``.
        category : Optional[str]
            The optional category of the involved dataset or datasets, when applicable; defaults to ``None``.
        data_location : Optional[str]
            Optional location/file/object/etc. for acted-upon data.
        is_pending_data : bool
            Whether the sender has data pending transmission after this message (default: ``False``).
        query : Optional[DatasetQuery]
            Optional ::class:`DatasetQuery` object for query messages.
        """
        # Sanity check certain param values depending on the action; e.g., can't CREATE a dataset without a name
        err_msg_template = "Cannot create {} for action {} without {}"
        if dataset_name is None and action.requires_dataset_name:
            raise RuntimeError(err_msg_template.format(self.__class__.__name__, action, "a dataset name"))
        if category is None and action.requires_data_category:
            raise RuntimeError(err_msg_template.format(self.__class__.__name__, action, "a data category"))
        if domain is None and action.requires_data_domain:
            raise RuntimeError(err_msg_template.format(self.__class__.__name__, action, "a data domain"))

        super(DatasetManagementMessage, self).__init__(*args, **kwargs)

        # TODO: raise exceptions for actions for which the workflow is not yet supported (e.g., REMOVE_DATA)

        self._action = action
        self._dataset_name = dataset_name
        self._is_read_only_dataset = is_read_only_dataset
        self._category = category
        self._domain = domain
        self._data_location = data_location
        self._query = query
        self._is_pending_data = is_pending_data

    @property
    def data_location(self) -> Optional[str]:
        """
        Location for acted-upon data.

        Returns
        -------
        Optional[str]
            Location for acted-upon data.
        """
        return self._data_location

    @property
    def is_pending_data(self) -> bool:
        """
        Whether the sender has data pending transmission after this message.

        Whether the sender has data it wants to transmit after this message.  The typical use case is during a
        ``CREATE`` action, where this indicates there is already data to add to the newly created dataset.

        Returns
        -------
        bool
            Whether the sender has data pending transmission after this message.
        """
        return self._is_pending_data

    @property
    def data_category(self) -> Optional[DataCategory]:
        """
        The category of the involved data, if applicable.

        Returns
        -------
        bool
            The category of the involved data, if applicable.
        """
        return self._category

    @property
    def data_domain(self) -> Optional[DataDomain]:
        """
        The domain of the involved data, if applicable.

        Returns
        -------
        Optional[DataDomain]
            The domain of the involved data, if applicable.
        """
        return self._domain

    @property
    def dataset_name(self) -> Optional[str]:
        """
        The name of the involved dataset, if applicable.

        Returns
        -------
        Optional
            The name of the involved dataset, if applicable.
        """
        return self._dataset_name

    @property
    def is_read_only_dataset(self) -> bool:
        """
        Whether the dataset involved is, should be, or must be (depending on action) read-only.

        Returns
        -------
        bool
            Whether the dataset involved is, should be, or must be (depending on action) read-only.
        """
        return self._is_read_only_dataset

    @property
    def management_action(self) -> ManagementAction:
        """
        The type of ::class:`ManagementAction` this message embodies or requests.

        Returns
        -------
        ManagementAction
            The type of ::class:`ManagementAction` this message embodies or requests.
        """
        return self._action

    @property
    def query(self) -> Optional[DatasetQuery]:
        return self._query

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        serial = {self._SERIAL_KEY_ACTION: self.management_action.name,
                  self._SERIAL_KEY_IS_READ_ONLY: self.is_read_only_dataset,
                  self._SERIAL_KEY_IS_PENDING_DATA: self.is_pending_data}
        if self.dataset_name is not None:
            serial[self._SERIAL_KEY_DATASET_NAME] = self.dataset_name
        if self.data_category is not None:
            serial[self._SERIAL_KEY_CATEGORY] = self.data_category.name
        if self.data_location is not None:
            serial[self._SERIAL_KEY_DATA_LOCATION] = self.data_location
        if self.data_domain is not None:
            serial[self._SERIAL_KEY_DATA_DOMAIN] = self.data_domain.to_dict()
        if self.query is not None:
            serial[self._SERIAL_KEY_QUERY] = self.query.to_dict()
        return serial


class DatasetManagementResponse(Response):

    _DATA_KEY_ACTION= 'action'
    _DATA_KEY_DATA_ID = 'data_id'
    _DATA_KEY_DATASET_NAME = 'dataset_name'
    _DATA_KEY_ITEM_NAME = 'item_name'
    _DATA_KEY_QUERY_RESULTS = 'query_results'
    _DATA_KEY_IS_AWAITING = 'is_awaiting'
    response_to_type = DatasetManagementMessage

    def __init__(self, action: Optional[ManagementAction] = None, is_awaiting: bool = False,
                 data_id: Optional[str] = None, dataset_name: Optional[str] = None, data: Optional[dict] = None,
                 **kwargs):
        if data is None:
            data = {}

        # Make sure 'action' param and action string within 'data' param aren't both present and conflicting
        if action is not None:
            if action.name != data.get(self._DATA_KEY_ACTION, action.name):
                msg = '{} initialized with {} action param, but {} action in initial data.'
                raise ValueError(msg.format(self.__class__.__name__, action.name, data.get(self._DATA_KEY_ACTION)))
            data[self._DATA_KEY_ACTION] = action.name
        # Additionally, if not using an explicit 'action', make sure it's a valid action string in 'data', or bail
        else:
            data_action_str = data.get(self._DATA_KEY_ACTION, '')
            # Compare the string to the 'name' string of the action value obtain by passing the string to get_for_name()
            if data_action_str.strip().upper() != ManagementAction.get_for_name(data_action_str).name.upper():
                msg = "No valid action param or within 'data' when initializing {} instance (received only '{}')"
                raise ValueError(msg.format(self.__class__.__name__, data_action_str))

        data[self._DATA_KEY_IS_AWAITING] = is_awaiting
        if data_id is not None:
            data[self._DATA_KEY_DATA_ID] = data_id
        if dataset_name is not None:
            data[self._DATA_KEY_DATASET_NAME] = dataset_name
        super().__init__(data=data, **kwargs)

    @property
    def action(self) -> ManagementAction:
        """
        The action requested by the ::class:`DatasetManagementMessage` for which this instance is the response.

        Returns
        -------
        ManagementAction
            The action requested by the ::class:`DatasetManagementMessage` for which this instance is the response.
        """
        if self._DATA_KEY_ACTION not in self.data:
            return ManagementAction.UNKNOWN
        elif isinstance(self.data[self._DATA_KEY_ACTION], str):
            return ManagementAction.get_for_name(self.data[self._DATA_KEY_ACTION])
        elif isinstance(self.data[self._DATA_KEY_ACTION], ManagementAction):
            val = self.data[self._DATA_KEY_ACTION]
            self.data[self._DATA_KEY_ACTION] = val.name
            return val
        else:
            return ManagementAction.UNKNOWN

    @property
    def data_id(self) -> Optional[str]:
        """
        When available, the 'data_id' of the related dataset.

        Returns
        -------
        Optional[str]
            When available, the 'data_id' of the related dataset.
        """
        return self.data[self._DATA_KEY_DATA_ID] if self._DATA_KEY_DATA_ID in self.data else None

    @property
    def dataset_name(self) -> Optional[str]:
        """
        When available, the name of the relevant dataset.

        Returns
        -------
        Optional[str]
            When available, the name of the relevant dataset; otherwise ``None``.
        """
        return self.data[self._DATA_KEY_DATASET_NAME] if self._DATA_KEY_DATASET_NAME in self.data else None

    @property
    def item_name(self) -> Optional[str]:
        """
        When available/appropriate, the name of the relevant dataset item/object/file.

        Returns
        -------
        Optional[str]
            The name of the relevant dataset item/object/file, or ``None``.
        """
        return self.data.get(self._DATA_KEY_ITEM_NAME)

    @property
    def query_results(self) -> Optional[dict]:
        return self.data.get(self._DATA_KEY_QUERY_RESULTS)

    @property
    def is_awaiting(self) -> bool:
        """
        Whether the response, in addition to success, indicates the response sender is awaiting something additional.

        Typically, this is an indication that the responder side is ready and expecting additional follow-up messages
        from the originator.  For example, after responding to a successful ``CREATE``, a message may set that it is
        in the awaiting state to wait for data to be uploaded by the originator for insertion into the new dataset.

        Returns
        -------
        bool
            Whether the response indicates the response sender is awaiting something additional.
        """
        return self.data[self._DATA_KEY_IS_AWAITING]


class MaaSDatasetManagementMessage(DatasetManagementMessage, ExternalRequest):
    """
    A publicly initiated, and thus session authenticated, extension of ::class:`DatasetManagementMessage`.

    Note that message hashes and equality do not consider session secret, to be compatible with the implementations in
    the superclass.
    """

    _SERIAL_KEY_DATA_REQUIREMENTS = 'data_requirements'
    _SERIAL_KEY_OUTPUT_FORMATS = 'output_formats'
    _SERIAL_KEY_SESSION_SECRET = 'session_secret'

    @classmethod
    def factory_create(cls, mgmt_msg: DatasetManagementMessage, session_secret: str) -> 'MaaSDatasetManagementMessage':
        return cls(session_secret=session_secret, action=mgmt_msg.management_action, dataset_name=mgmt_msg.dataset_name,
                   is_read_only_dataset=mgmt_msg.is_read_only_dataset, category=mgmt_msg.data_category,
                   domain=mgmt_msg.data_domain, data_location=mgmt_msg.data_location,
                   is_pending_data=mgmt_msg.is_pending_data)

    @classmethod
    def factory_init_correct_response_subtype(cls, json_obj: dict) -> 'MaaSDatasetManagementResponse':
        """
        Init a :obj:`Response` instance of the appropriate subtype for this class from the provided JSON object.

        Parameters
        ----------
        json_obj

        Returns
        -------

        """
        return MaaSDatasetManagementResponse.factory_init_from_deserialized_json(json_obj=json_obj)

    @classmethod
    def factory_init_from_deserialized_json(cls, json_obj: dict) -> Optional['MaaSDatasetManagementMessage']:
        try:
            # Inject this if necessary before passing to supertype
            if 'deserialized_class' not in json_obj:
                json_obj['deserialized_class'] = cls
            elif isinstance(json_obj['deserialized_class'], str):
                json_obj['deserialized_class'] = globals()[json_obj['deserialized_class']]
            # Also inject things that will be used as additional kwargs to the eventual class init
            if 'deserialized_class_kwargs' not in json_obj:
                json_obj['deserialized_class_kwargs'] = dict()
            if 'session_secret' not in json_obj['deserialized_class_kwargs']:
                json_obj['deserialized_class_kwargs']['session_secret'] = json_obj[cls._SERIAL_KEY_SESSION_SECRET]

            obj = super().factory_init_from_deserialized_json(json_obj=json_obj)

            # Also add these if there happened to be any present
            if cls._SERIAL_KEY_DATA_REQUIREMENTS in json_obj:
                obj.data_requirements.extend([DataRequirement.factory_init_from_deserialized_json(json) for json in
                                              json_obj[cls._SERIAL_KEY_DATA_REQUIREMENTS]])
            if cls._SERIAL_KEY_OUTPUT_FORMATS in json_obj:
                obj.output_formats.extend(
                    [DataFormat.get_for_name(f) for f in json_obj[cls._SERIAL_KEY_OUTPUT_FORMATS]])

            # Finally, return the object
            return obj
        except Exception as e:
            return None

    def __init__(self, session_secret: str, *args, **kwargs):
        """

        Keyword Args
        ----------
        session_secret : str
        action : ManagementAction
        dataset_name : Optional[str]
        is_read_only_dataset : bool
        category : Optional[DataCategory]
        data_location : Optional[str]
        is_pending_data : bool
        query : Optional[DataQuery]
        """
        super(MaaSDatasetManagementMessage, self).__init__(session_secret=session_secret, *args, **kwargs)
        self._data_requirements = []
        self._output_formats = []

    @property
    def data_requirements(self) -> List[DataRequirement]:
        """
        List of all the explicit and implied data requirements for this request.

        By default, this is an empty list, though it is possible to append requirements to the list.

        Returns
        -------
        List[DataRequirement]
            List of all the explicit and implied data requirements for this request.
        """
        return self._data_requirements

    @property
    def output_formats(self) -> List[DataFormat]:
        """
        List of the formats of each required output dataset for the requested task.

        By default, this will be an empty list, though if any request does need to produce output, formats can be
        appended to it

        Returns
        -------
        List[DataFormat]
            List of the formats of each required output dataset for the requested.
        """
        return self._output_formats

    def to_dict(self) -> Dict[str, Union[str, Number, dict, list]]:
        serial = super(MaaSDatasetManagementMessage, self).to_dict()
        serial[self._SERIAL_KEY_SESSION_SECRET] = self.session_secret
        if len(self.data_requirements) > 0:
            serial[self._SERIAL_KEY_DATA_REQUIREMENTS] = [r.to_dict() for r in self.data_requirements]
        if len(self.output_formats) > 0:
            serial[self._SERIAL_KEY_OUTPUT_FORMATS] = [f.name for f in self.output_formats]
        return serial


class MaaSDatasetManagementResponse(ExternalRequestResponse, DatasetManagementResponse):
    """
    Analog of ::class:`DatasetManagementResponse`, but for the ::class:`MaaSDatasetManagementMessage` message type.
    """

    response_to_type = MaaSDatasetManagementMessage

    @classmethod
    def factory_create(cls, dataset_mgmt_response: DatasetManagementResponse) -> 'MaaSDatasetManagementResponse':
        """
        Create an instance from the non-session-based ::class:`DatasetManagementResponse`.

        Parameters
        ----------
        dataset_mgmt_response : DatasetManagementResponse
            Analogous instance of the non-session type.

        Returns
        -------
        MaaSDatasetManagementResponse
            Factory-created analog of this instance type.
        """
        return cls.factory_init_from_deserialized_json(dataset_mgmt_response.to_dict())