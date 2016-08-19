# Copyright 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Connections to gcloud datastore API servers."""

import os

from google.rpc import status_pb2

from gcloud._helpers import make_stub
from gcloud import connection as connection_module
from gcloud.environment_vars import GCD_HOST
from gcloud.exceptions import Conflict
from gcloud.exceptions import make_exception
from gcloud.datastore._generated import datastore_pb2 as _datastore_pb2
# pylint: disable=ungrouped-imports
try:
    from grpc import StatusCode
    from grpc._channel import _Rendezvous
    from gcloud.datastore._generated import datastore_grpc_pb2
except ImportError:  # pragma: NO COVER
    _HAVE_GRPC = False
    datastore_grpc_pb2 = None
    StatusCode = None
    _Rendezvous = Exception
else:
    _HAVE_GRPC = True
# pylint: enable=ungrouped-imports


DATASTORE_API_HOST = 'datastore.googleapis.com'
"""Datastore API request host."""
DATASTORE_API_PORT = 443
"""Datastore API request port."""
GRPC_TIMEOUT_SECONDS = 10
"""The default timeout to use for API requests via gRPC."""


class _DatastoreAPIOverHttp(object):
    """Helper mapping datastore API methods.

    Makes requests to send / receive protobuf content over HTTP/1.1.

    Methods make bare API requests without any helpers for constructing
    the requests or parsing the responses.

    :type connection: :class:`gcloud.datastore.connection.Connection`
    :param connection: A connection object that contains helpful
                       information for making requests.
    """

    def __init__(self, connection):
        self.connection = connection

    def _request(self, project, method, data):
        """Make a request over the Http transport to the Cloud Datastore API.

        :type project: string
        :param project: The project to make the request for.

        :type method: string
        :param method: The API call method name (ie, ``runQuery``,
                       ``lookup``, etc)

        :type data: string
        :param data: The data to send with the API call.
                     Typically this is a serialized Protobuf string.

        :rtype: string
        :returns: The string response content from the API call.
        :raises: :class:`gcloud.exceptions.GCloudError` if the response
                 code is not 200 OK.
        """
        headers = {
            'Content-Type': 'application/x-protobuf',
            'Content-Length': str(len(data)),
            'User-Agent': self.connection.USER_AGENT,
        }
        headers, content = self.connection.http.request(
            uri=self.connection.build_api_url(project=project, method=method),
            method='POST', headers=headers, body=data)

        status = headers['status']
        if status != '200':
            error_status = status_pb2.Status.FromString(content)
            raise make_exception(headers, error_status.message, use_json=False)

        return content

    def _rpc(self, project, method, request_pb, response_pb_cls):
        """Make a protobuf RPC request.

        :type project: string
        :param project: The project to connect to. This is
                        usually your project name in the cloud console.

        :type method: string
        :param method: The name of the method to invoke.

        :type request_pb: :class:`google.protobuf.message.Message` instance
        :param request_pb: the protobuf instance representing the request.

        :type response_pb_cls: A :class:`google.protobuf.message.Message`
                               subclass.
        :param response_pb_cls: The class used to unmarshall the response
                                protobuf.

        :rtype: :class:`google.protobuf.message.Message`
        :returns: The RPC message parsed from the response.
        """
        response = self._request(project=project, method=method,
                                 data=request_pb.SerializeToString())
        return response_pb_cls.FromString(response)

    def lookup(self, project, request_pb):
        """Perform a ``lookup`` request.

        :type project: string
        :param project: The project to connect to. This is
                        usually your project name in the cloud console.

        :type request_pb: :class:`._generated.datastore_pb2.LookupRequest`
        :param request_pb: The request protobuf object.

        :rtype: :class:`._generated.datastore_pb2.LookupResponse`
        :returns: The returned protobuf response object.
        """
        return self._rpc(project, 'lookup', request_pb,
                         _datastore_pb2.LookupResponse)

    def run_query(self, project, request_pb):
        """Perform a ``runQuery`` request.

        :type project: string
        :param project: The project to connect to. This is
                        usually your project name in the cloud console.

        :type request_pb: :class:`._generated.datastore_pb2.RunQueryRequest`
        :param request_pb: The request protobuf object.

        :rtype: :class:`._generated.datastore_pb2.RunQueryResponse`
        :returns: The returned protobuf response object.
        """
        return self._rpc(project, 'runQuery', request_pb,
                         _datastore_pb2.RunQueryResponse)

    def begin_transaction(self, project, request_pb):
        """Perform a ``beginTransaction`` request.

        :type project: string
        :param project: The project to connect to. This is
                        usually your project name in the cloud console.

        :type request_pb:
            :class:`._generated.datastore_pb2.BeginTransactionRequest`
        :param request_pb: The request protobuf object.

        :rtype: :class:`._generated.datastore_pb2.BeginTransactionResponse`
        :returns: The returned protobuf response object.
        """
        return self._rpc(project, 'beginTransaction', request_pb,
                         _datastore_pb2.BeginTransactionResponse)

    def commit(self, project, request_pb):
        """Perform a ``commit`` request.

        :type project: string
        :param project: The project to connect to. This is
                        usually your project name in the cloud console.

        :type request_pb: :class:`._generated.datastore_pb2.CommitRequest`
        :param request_pb: The request protobuf object.

        :rtype: :class:`._generated.datastore_pb2.CommitResponse`
        :returns: The returned protobuf response object.
        """
        return self._rpc(project, 'commit', request_pb,
                         _datastore_pb2.CommitResponse)

    def rollback(self, project, request_pb):
        """Perform a ``rollback`` request.

        :type project: string
        :param project: The project to connect to. This is
                        usually your project name in the cloud console.

        :type request_pb: :class:`._generated.datastore_pb2.RollbackRequest`
        :param request_pb: The request protobuf object.

        :rtype: :class:`._generated.datastore_pb2.RollbackResponse`
        :returns: The returned protobuf response object.
        """
        return self._rpc(project, 'rollback', request_pb,
                         _datastore_pb2.RollbackResponse)

    def allocate_ids(self, project, request_pb):
        """Perform an ``allocateIds`` request.

        :type project: string
        :param project: The project to connect to. This is
                        usually your project name in the cloud console.

        :type request_pb: :class:`._generated.datastore_pb2.AllocateIdsRequest`
        :param request_pb: The request protobuf object.

        :rtype: :class:`._generated.datastore_pb2.AllocateIdsResponse`
        :returns: The returned protobuf response object.
        """
        return self._rpc(project, 'allocateIds', request_pb,
                         _datastore_pb2.AllocateIdsResponse)


class _DatastoreAPIOverGRPC(object):
    """Helper mapping datastore API methods.

    Makes requests to send / receive protobuf content over gRPC.

    Methods make bare API requests without any helpers for constructing
    the requests or parsing the responses.

    :type connection: :class:`gcloud.datastore.connection.Connection`
    :param connection: A connection object that contains helpful
                       information for making requests.
    """

    def __init__(self, connection):
        self._stub = make_stub(connection.credentials, connection.USER_AGENT,
                               datastore_grpc_pb2.DatastoreStub,
                               DATASTORE_API_HOST, DATASTORE_API_PORT)

    def lookup(self, project, request_pb):
        """Perform a ``lookup`` request.

        :type project: string
        :param project: The project to connect to. This is
                        usually your project name in the cloud console.

        :type request_pb: :class:`._generated.datastore_pb2.LookupRequest`
        :param request_pb: The request protobuf object.

        :rtype: :class:`._generated.datastore_pb2.LookupResponse`
        :returns: The returned protobuf response object.
        """
        request_pb.project_id = project
        return self._stub.Lookup(request_pb, GRPC_TIMEOUT_SECONDS)

    def run_query(self, project, request_pb):
        """Perform a ``runQuery`` request.

        :type project: string
        :param project: The project to connect to. This is
                        usually your project name in the cloud console.

        :type request_pb: :class:`._generated.datastore_pb2.RunQueryRequest`
        :param request_pb: The request protobuf object.

        :rtype: :class:`._generated.datastore_pb2.RunQueryResponse`
        :returns: The returned protobuf response object.
        """
        request_pb.project_id = project
        return self._stub.RunQuery(request_pb, GRPC_TIMEOUT_SECONDS)

    def begin_transaction(self, project, request_pb):
        """Perform a ``beginTransaction`` request.

        :type project: string
        :param project: The project to connect to. This is
                        usually your project name in the cloud console.

        :type request_pb:
            :class:`._generated.datastore_pb2.BeginTransactionRequest`
        :param request_pb: The request protobuf object.

        :rtype: :class:`._generated.datastore_pb2.BeginTransactionResponse`
        :returns: The returned protobuf response object.
        """
        request_pb.project_id = project
        return self._stub.BeginTransaction(request_pb, GRPC_TIMEOUT_SECONDS)

    def commit(self, project, request_pb):
        """Perform a ``commit`` request.

        :type project: string
        :param project: The project to connect to. This is
                        usually your project name in the cloud console.

        :type request_pb: :class:`._generated.datastore_pb2.CommitRequest`
        :param request_pb: The request protobuf object.

        :rtype: :class:`._generated.datastore_pb2.CommitResponse`
        :returns: The returned protobuf response object.
        """
        request_pb.project_id = project
        try:
            return self._stub.Commit(request_pb, GRPC_TIMEOUT_SECONDS)
        except _Rendezvous as exc:
            if exc.code() == StatusCode.ABORTED:
                raise Conflict(exc.details())
            raise

    def rollback(self, project, request_pb):
        """Perform a ``rollback`` request.

        :type project: string
        :param project: The project to connect to. This is
                        usually your project name in the cloud console.

        :type request_pb: :class:`._generated.datastore_pb2.RollbackRequest`
        :param request_pb: The request protobuf object.

        :rtype: :class:`._generated.datastore_pb2.RollbackResponse`
        :returns: The returned protobuf response object.
        """
        request_pb.project_id = project
        return self._stub.Rollback(request_pb, GRPC_TIMEOUT_SECONDS)

    def allocate_ids(self, project, request_pb):
        """Perform an ``allocateIds`` request.

        :type project: string
        :param project: The project to connect to. This is
                        usually your project name in the cloud console.

        :type request_pb: :class:`._generated.datastore_pb2.AllocateIdsRequest`
        :param request_pb: The request protobuf object.

        :rtype: :class:`._generated.datastore_pb2.AllocateIdsResponse`
        :returns: The returned protobuf response object.
        """
        request_pb.project_id = project
        return self._stub.AllocateIds(request_pb, GRPC_TIMEOUT_SECONDS)


class Connection(connection_module.Connection):
    """A connection to the Google Cloud Datastore via the Protobuf API.

    This class should understand only the basic types (and protobufs)
    in method arguments, however should be capable of returning advanced types.

    :type credentials: :class:`oauth2client.client.OAuth2Credentials`
    :param credentials: The OAuth2 Credentials to use for this connection.

    :type http: :class:`httplib2.Http` or class that defines ``request()``.
    :param http: An optional HTTP object to make requests.

    :type api_base_url: string
    :param api_base_url: The base of the API call URL. Defaults to
                         :attr:`API_BASE_URL`.
    """

    API_BASE_URL = 'https://' + DATASTORE_API_HOST
    """The base of the API call URL."""

    API_VERSION = 'v1'
    """The version of the API, used in building the API call's URL."""

    API_URL_TEMPLATE = ('{api_base}/{api_version}/projects'
                        '/{project}:{method}')
    """A template for the URL of a particular API call."""

    SCOPE = ('https://www.googleapis.com/auth/datastore',)
    """The scopes required for authenticating as a Cloud Datastore consumer."""

    def __init__(self, credentials=None, http=None, api_base_url=None):
        super(Connection, self).__init__(credentials=credentials, http=http)
        if api_base_url is None:
            try:
                # gcd.sh has /datastore/ in the path still since it supports
                # v1beta2 and v1beta3 simultaneously.
                api_base_url = '%s/datastore' % (os.environ[GCD_HOST],)
            except KeyError:
                api_base_url = self.__class__.API_BASE_URL
        self.api_base_url = api_base_url
        if _HAVE_GRPC:
            self._datastore_api = _DatastoreAPIOverGRPC(self)
        else:
            self._datastore_api = _DatastoreAPIOverHttp(self)

    def build_api_url(self, project, method, base_url=None,
                      api_version=None):
        """Construct the URL for a particular API call.

        This method is used internally to come up with the URL to use when
        making RPCs to the Cloud Datastore API.

        :type project: string
        :param project: The project to connect to. This is
                        usually your project name in the cloud console.

        :type method: string
        :param method: The API method to call (e.g. 'runQuery', 'lookup').

        :type base_url: string
        :param base_url: The base URL where the API lives.
                         You shouldn't have to provide this.

        :type api_version: string
        :param api_version: The version of the API to connect to.
                            You shouldn't have to provide this.

        :rtype: str
        :returns: The API URL created.
        """
        return self.API_URL_TEMPLATE.format(
            api_base=(base_url or self.api_base_url),
            api_version=(api_version or self.API_VERSION),
            project=project, method=method)

    def lookup(self, project, key_pbs,
               eventual=False, transaction_id=None):
        """Lookup keys from a project in the Cloud Datastore.

        Maps the ``DatastoreService.Lookup`` protobuf RPC.

        This uses mostly protobufs
        (:class:`gcloud.datastore._generated.entity_pb2.Key` as input and
        :class:`gcloud.datastore._generated.entity_pb2.Entity` as output). It
        is used under the hood in
        :meth:`Client.get() <.datastore.client.Client.get>`:

        >>> from gcloud import datastore
        >>> client = datastore.Client(project='project')
        >>> key = client.key('MyKind', 1234)
        >>> client.get(key)
        [<Entity object>]

        Using a :class:`Connection` directly:

        >>> connection.lookup('project', [key.to_protobuf()])
        [<Entity protobuf>]

        :type project: string
        :param project: The project to look up the keys in.

        :type key_pbs: list of
                       :class:`gcloud.datastore._generated.entity_pb2.Key`
        :param key_pbs: The keys to retrieve from the datastore.

        :type eventual: bool
        :param eventual: If False (the default), request ``STRONG`` read
                         consistency.  If True, request ``EVENTUAL`` read
                         consistency.

        :type transaction_id: string
        :param transaction_id: If passed, make the request in the scope of
                               the given transaction.  Incompatible with
                               ``eventual==True``.

        :rtype: tuple
        :returns: A triple of (``results``, ``missing``, ``deferred``) where
                  both ``results`` and ``missing`` are lists of
                  :class:`gcloud.datastore._generated.entity_pb2.Entity` and
                  ``deferred`` is a list of
                  :class:`gcloud.datastore._generated.entity_pb2.Key`.
        """
        lookup_request = _datastore_pb2.LookupRequest()
        _set_read_options(lookup_request, eventual, transaction_id)
        _add_keys_to_request(lookup_request.keys, key_pbs)

        lookup_response = self._datastore_api.lookup(project, lookup_request)

        results = [result.entity for result in lookup_response.found]
        missing = [result.entity for result in lookup_response.missing]

        return results, missing, list(lookup_response.deferred)

    def run_query(self, project, query_pb, namespace=None,
                  eventual=False, transaction_id=None):
        """Run a query on the Cloud Datastore.

        Maps the ``DatastoreService.RunQuery`` protobuf RPC.

        Given a Query protobuf, sends a ``runQuery`` request to the
        Cloud Datastore API and returns a list of entity protobufs
        matching the query.

        You typically wouldn't use this method directly, in favor of the
        :meth:`gcloud.datastore.query.Query.fetch` method.

        Under the hood, the :class:`gcloud.datastore.query.Query` class
        uses this method to fetch data.

        :type project: string
        :param project: The project over which to run the query.

        :type query_pb: :class:`gcloud.datastore._generated.query_pb2.Query`
        :param query_pb: The Protobuf representing the query to run.

        :type namespace: string
        :param namespace: The namespace over which to run the query.

        :type eventual: bool
        :param eventual: If False (the default), request ``STRONG`` read
                         consistency.  If True, request ``EVENTUAL`` read
                         consistency.

        :type transaction_id: string
        :param transaction_id: If passed, make the request in the scope of
                               the given transaction.  Incompatible with
                               ``eventual==True``.

        :rtype: tuple
        :returns: Four-tuple containing the entities returned,
                  the end cursor of the query, a ``more_results``
                  enum and a count of the number of skipped results.
        """
        request = _datastore_pb2.RunQueryRequest()
        _set_read_options(request, eventual, transaction_id)

        if namespace:
            request.partition_id.namespace_id = namespace

        request.query.CopyFrom(query_pb)
        response = self._datastore_api.run_query(project, request)
        return (
            [e.entity for e in response.batch.entity_results],
            response.batch.end_cursor,  # Assume response always has cursor.
            response.batch.more_results,
            response.batch.skipped_results,
        )

    def begin_transaction(self, project):
        """Begin a transaction.

        Maps the ``DatastoreService.BeginTransaction`` protobuf RPC.

        :type project: string
        :param project: The project to which the transaction applies.

        :rtype: bytes
        :returns: The serialized transaction that was begun.
        """
        request = _datastore_pb2.BeginTransactionRequest()
        response = self._datastore_api.begin_transaction(project, request)
        return response.transaction

    def commit(self, project, request, transaction_id):
        """Commit mutations in context of current transation (if any).

        Maps the ``DatastoreService.Commit`` protobuf RPC.

        :type project: string
        :param project: The project to which the transaction applies.

        :type request: :class:`._generated.datastore_pb2.CommitRequest`
        :param request: The protobuf with the mutations being committed.

        :type transaction_id: string or None
        :param transaction_id: The transaction ID returned from
                               :meth:`begin_transaction`.  Non-transactional
                               batches must pass ``None``.

        .. note::

            This method will mutate ``request`` before using it.

        :rtype: tuple
        :returns: The pair of the number of index updates and a list of
                  :class:`._generated.entity_pb2.Key` for each incomplete key
                  that was completed in the commit.
        """
        if transaction_id:
            request.mode = _datastore_pb2.CommitRequest.TRANSACTIONAL
            request.transaction = transaction_id
        else:
            request.mode = _datastore_pb2.CommitRequest.NON_TRANSACTIONAL

        response = self._datastore_api.commit(project, request)
        return _parse_commit_response(response)

    def rollback(self, project, transaction_id):
        """Rollback the connection's existing transaction.

        Maps the ``DatastoreService.Rollback`` protobuf RPC.

        :type project: string
        :param project: The project to which the transaction belongs.

        :type transaction_id: string
        :param transaction_id: The transaction ID returned from
                               :meth:`begin_transaction`.
        """
        request = _datastore_pb2.RollbackRequest()
        request.transaction = transaction_id
        # Nothing to do with this response, so just execute the method.
        self._datastore_api.rollback(project, request)

    def allocate_ids(self, project, key_pbs):
        """Obtain backend-generated IDs for a set of keys.

        Maps the ``DatastoreService.AllocateIds`` protobuf RPC.

        :type project: string
        :param project: The project to which the transaction belongs.

        :type key_pbs: list of
                       :class:`gcloud.datastore._generated.entity_pb2.Key`
        :param key_pbs: The keys for which the backend should allocate IDs.

        :rtype: list of :class:`gcloud.datastore._generated.entity_pb2.Key`
        :returns: An equal number of keys,  with IDs filled in by the backend.
        """
        request = _datastore_pb2.AllocateIdsRequest()
        _add_keys_to_request(request.keys, key_pbs)
        # Nothing to do with this response, so just execute the method.
        response = self._datastore_api.allocate_ids(project, request)
        return list(response.keys)


def _set_read_options(request, eventual, transaction_id):
    """Validate rules for read options, and assign to the request.

    Helper method for ``lookup()`` and ``run_query``.

    :raises: :class:`ValueError` if ``eventual`` is ``True`` and the
             ``transaction_id`` is not ``None``.
    """
    if eventual and (transaction_id is not None):
        raise ValueError('eventual must be False when in a transaction')

    opts = request.read_options
    if eventual:
        opts.read_consistency = _datastore_pb2.ReadOptions.EVENTUAL
    elif transaction_id:
        opts.transaction = transaction_id


def _add_keys_to_request(request_field_pb, key_pbs):
    """Add protobuf keys to a request object.

    :type request_field_pb: `RepeatedCompositeFieldContainer`
    :param request_field_pb: A repeated proto field that contains keys.

    :type key_pbs: list of :class:`gcloud.datastore._generated.entity_pb2.Key`
    :param key_pbs: The keys to add to a request.
    """
    for key_pb in key_pbs:
        request_field_pb.add().CopyFrom(key_pb)


def _parse_commit_response(commit_response_pb):
    """Extract response data from a commit response.

    :type commit_response_pb: :class:`._generated.datastore_pb2.CommitResponse`
    :param commit_response_pb: The protobuf response from a commit request.

    :rtype: tuple
    :returns: The pair of the number of index updates and a list of
              :class:`._generated.entity_pb2.Key` for each incomplete key
              that was completed in the commit.
    """
    mut_results = commit_response_pb.mutation_results
    index_updates = commit_response_pb.index_updates
    completed_keys = [mut_result.key for mut_result in mut_results
                      if mut_result.HasField('key')]  # Message field (Key)
    return index_updates, completed_keys
