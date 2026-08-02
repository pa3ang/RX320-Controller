import socket
import time


class DXCluster:

    def __init__(
            self,
            host,
            port=8000,
            call=None,
            filters=None,
            callback=None):

        self.host = host
        self.port = port
        self.call = call
        self.filters = filters or []
        self.callback = callback

        self.sock = None
        self.running = False
        self.logged_in = False
        self.filters_sent = False

        print("INIT:")
        print("host =", self.host)
        print("port =", self.port)
        print("call =", repr(self.call))
        print("filters =", self.filters)


    def connect(self):

        while True:

            try:
                print("Connecting to:", self.host, self.port)

                self.sock = socket.socket(
                    socket.AF_INET,
                    socket.SOCK_STREAM
                )

                self.sock.settimeout(30)

                self.sock.connect(
                    (self.host, self.port)
                )

                self.sock.settimeout(None)

                self.running = True
                self.logged_in = False
                self.filters_sent = False

                print("DXCluster connected")

                self.read_thread()


            except Exception as e:

                print(
                    "DXCluster connect error:",
                    e
                )


            finally:

                self.running = False

                try:
                    if self.sock:
                        self.sock.close()

                except:
                    pass


            print("Retry DXCluster in 10 seconds...")
            time.sleep(10)



    def send(self, text):

        try:

            print("TX:", repr(text))

            self.sock.sendall(
                (text + "\r\n").encode()
            )

        except Exception as e:

            print(
                "DXCluster send error:",
                e
            )



    def send_filters(self):

        print(">>> send_filters() gestart")
        print("Aantal filters:", len(self.filters))
        print("Filters inhoud:", repr(self.filters))


        if self.filters_sent:
            print("Filters waren al verzonden")
            return


        for cmd in self.filters:

            print("Origineel commando:", repr(cmd))

            cmd = cmd.strip()

            if not cmd:
                print("Leeg commando overgeslagen")
                continue


            print("FILTER TX:", repr(cmd))

            self.send(cmd)

            time.sleep(1)


        self.filters_sent = True

        print(">>> send_filters() klaar")


    def login_detected(self, line):

        """
        Herken dat de cluster login klaar is.
        Pas eventueel aanpassen als PI4CC een andere tekst geeft.
        """

        line = line.lower()


        if (
            "welcome" in line
            or "logged in" in line
            or "hello" in line
            or "dxcluster" in line
        ):

            return True


        return False



    def read_thread(self):

        buffer = ""


        while self.running:

            try:

                data = self.sock.recv(4096)


                if not data:

                    print(
                        "Server closed connection"
                    )

                    break



                text = data.decode(
                    errors="ignore"
                )


                print(
                    "RAW:",
                    repr(text)
                )



                # login prompt
                if (
                    not self.logged_in
                    and "login" in text.lower()
                ):

                    print(
                        "Sending callsign:",
                        self.call
                    )

                    self.send(
                        self.call
                    )



                buffer += text



                lines = buffer.split("\n")

                buffer = lines[-1]



                for line in lines[:-1]:

                    line = line.strip()
                    line=line.strip().replace("\x07","")

                    if not line:
                        continue



                    print(
                        "DX:",
                        line
                    )



                    # login bevestiging
                    if (
                        not self.logged_in
                        and self.login_detected(line)
                    ):

                        print(
                            "Login accepted"
                        )

                        self.logged_in = True


                        time.sleep(1)

                        self.send_filters()



                    if self.callback:

                        self.callback(line)



            except Exception as e:

                print(
                    "DXCluster read error:",
                    e
                )

                break



        self.running = False

        print(
            "DXCluster disconnected"
        )



    def close(self):

        self.running = False


        try:

            if self.sock:
                self.sock.close()


        except:

            pass
