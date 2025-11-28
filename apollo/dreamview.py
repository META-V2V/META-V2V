import json
from websocket import create_connection

class Dreamview:
    """
    Class to wrap Dreamview connection

    :param str ip: IP address of Dreamview websocket
    :param int port: port of Dreamview websocket
    """

    def __init__(self, ip: str, port: int) -> None:
        """
        Constructor
        """
        self.url = f"ws://{ip}:{port}/websocket"
        self.ws = create_connection(self.url)

    def send_data(self, data: dict) -> None:
        """
        Helper function to send data to Dreamview

        :param dict data: data to be sent
        """
        # ws = create_connection(self.url)
        # ws.send(json.dumps(data))
        # ws.close()
        self.ws.send(json.dumps(data))

    def start_sim_control(self) -> None:
        """
        Starts SimControl via websocket
        """
        self.send_data({
            "type": "StartSimControl"
        })

    def stop_sim_control(self) -> None:
        """
        Stops SimControl via websocket
        """
        self.send_data({
            "type": "StopSimControl"
        })

    def reset(self) -> None:
        """
        Resets Dreamview
        """
        self.send_data({
            "type": "Reset"
        })
