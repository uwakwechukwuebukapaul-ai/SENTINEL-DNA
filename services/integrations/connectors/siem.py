from ..connector import BaseConnector
class SyntheticSIEMConnector(BaseConnector): connector_name="synthetic_siem"; capabilities=("receive_events","health")
