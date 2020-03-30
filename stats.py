import datetime as dt

class CovidStats:
    def __init__(self):
        self.last_updated = dt.datetime.now()
        self.updated = True

        self.data = {"world": {}, "uk": {}, "sa": {}}

    def update_world(self, data):
        self.data["world"]["cases"] = int(data["latest"]["confirmed"])
        self.data["world"]["deaths"] = int(data["latest"]["deaths"])
        self.data["world"]["recovered"] = int(data["latest"]["recovered"])
    
    def update_country(self, data, country):
        update = dt.datetime.strptime(data["location"]["last_updated"], '%Y-%m-%dT%H:%M:%S.%fZ')
        if self.last_updated != update:
            self.last_updated = update
            self.updated = True

        self.data[country]["cases"] = int(data["location"]["latest"]["confirmed"])
        timeline = data["location"]["timelines"]["confirmed"]["timeline"]
        self.data[country]["recent_cases"] = int(timeline[list(timeline)[-1]]) - int(timeline[list(timeline)[-2]])
        self.data[country]["cases_timeline"] = timeline
        self.data[country]["deaths"] = int(data["location"]["latest"]["deaths"])
        timeline = data["location"]["timelines"]["deaths"]["timeline"]
        self.data[country]["recent_deaths"] = int(timeline[list(timeline)[-1]]) - int(timeline[list(timeline)[-2]])
        self.data[country]["deaths_timeline"] = timeline
        self.data[country]["recovered"] = int(data["location"]["latest"]["recovered"])

    def new_data(self):
        if self.updated:
            self.updated = False
            return True
        else:
            return False

    @property
    def confirmed(self):
        return "Confirmed: {0}\n  UK: {1} ({2})\n  SA: {3} ({4})".format(
            self.data["world"]["cases"], self.data["uk"]["cases"], self.data["uk"]["recent_cases"],
            self.data["sa"]["cases"], self.data["sa"]["recent_cases"]
        )

    @property
    def deaths(self):
        return "Deaths: {0}\n  UK: {1} ({2})\n  SA: {3} ({4})".format(
            self.data["world"]["deaths"], self.data["uk"]["deaths"], self.data["uk"]["recent_deaths"],
            self.data["sa"]["deaths"], self.data["sa"]["recent_deaths"]
        )

    def __repr__(self):
        fmt = """
Confirmed Cases:
  Total: {cw:d}
  UK:    {cuk:d}
  SA:    {csa:d}
Deaths:
  Total: {dw:d}
  UK:    {duk:d}
  SA:    {dw:d}
"""
        return fmt.format(
            cw=self.data["world"]["cases"],
            cuk=self.data["uk"]["cases"],
            csa=self.data["sa"]["cases"],
            dw=self.data["world"]["deaths"],
            duk=self.data["uk"]["deaths"],
            dsa=self.data["sa"]["deaths"]
        )
    
    __str__ = __repr__