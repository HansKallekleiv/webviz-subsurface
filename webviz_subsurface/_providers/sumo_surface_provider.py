import xtgeo, io
from sumo.wrapper import CallSumoApi


class SumoSurfaceProvider:
    def __init__(self, api=None, env=None):
        self.api = CallSumoApi(env)

    def search(self, sumo_parent_id=None, query=None, search_size=20):
        """Call Sumo, search for surfaces matching input arguments, return list of surfaces"""

        query_parts = []

        if sumo_parent_id:
            query_parts += [f"_sumo.parent_object:{sumo_parent_id}"]

        if query:
            query = query.replace("/", """\/""")
            query = (
                query.rstrip().lstrip()
            )  # remove leading/trailing spaces, will kill Sumo
            query_parts += query.split()

        assembled_query = " AND ".join(query_parts)

        print("query: {}".format(assembled_query))

        select = None
        response = self.api.search(
            assembled_query, select=select, search_size=search_size
        )

        hits = response.get("hits").get("hits")
        total = response.get("hits").get("total").get("value")
        return hits, total

    def get_cases(self):
        """
        Get list of available cases on Sumo.
        Return list of tuples (casename, sumo_ensemble_id)
        """

        url = (
            f"{self.api.base_url}/searchroot?"
            # f'$query=class.type:fmu_regularsurface'
            f"$query=*"
        )
        # print("Sumo:get_cases ", url)
        response = self.api.callAzureApi.get_json(url=url)
        hits = [hit for hit in response.get("hits").get("hits")]
        # print(hits)
        cases_and_ids = [
            {"case": hit.get("_source").get("fmu").get("case"), "id": hit.get("_id")}
            for hit in hits
        ]
        return cases_and_ids

    def get_iterations(self, parent):
        """
        Get list of available for a given case(parent) and content on Sumo.
        Return list of tuples (fmu_submodule, fmu_submodule)
        """
        url = (
            f"{self.api.base_url}/search?"
            # f"$query=class:surface AND "
            f"_sumo.parent_object:{parent}&"
            f"$buckets=fmu.iteration.name.keyword"
        )

        # print("Sumo:get_fmu_submodules ", url)
        response = self.api.callAzureApi.get_json(url=url)  # .get('hits').get('hits')

        aggregations = (
            response.get("aggregations")
            .get("fmu.iteration.name.keyword")
            .get("buckets")
        )
        iterations = [hit.get("key") for hit in aggregations]
        return iterations

    def get_contents(self, parent, iteration):
        """
        Get list of available Contents for a case(parent) on Sumo.
        Return list of tuples (contents, contents)
        """
        url = (
            f"{self.api.base_url}/search?"
            f"$query=class:surface AND _sumo.parent_object:{parent} AND "
            f"fmu.iteration.name:{iteration}&"
            f"$buckets=data.content.keyword"
        )
        # print("Sumo:get_contents ", url)
        response = self.api.callAzureApi.get_json(url=url)  # .get('hits').get('hits')
        aggregations = (
            response.get("aggregations").get("data.content.keyword").get("buckets")
        )
        contents = [hit.get("key") for hit in aggregations]
        return contents

    def get_surfaces(self, parent, iteration, content):
        """
        Get list of avialble sufaces(names) for a given case(parent) content and fmu_submodules on Sumo.
        Return list of tuples (surfaces, surfaces)
        """
        url = (
            f"{self.api.base_url}/search?"
            f"$query=class:surface AND "
            f"_sumo.parent_object:{parent} AND "
            f"data.content.keyword:{content} AND "
            f"fmu.iteration.name:{iteration}&"
            f"$buckets=data.name.keyword"
        )
        # print("Sumo:get_surfaces ", url)
        response = self.api.callAzureApi.get_json(url=url)  # .get('hits').get('hits')
        aggregations = (
            response.get("aggregations").get("data.name.keyword").get("buckets")
        )
        surfaces = [hit.get("key") for hit in aggregations]
        return surfaces

    def get_realizations(self, parent, iteration, content, surface):
        """
        Get list of available realizations/statistics for a given case(parent)
        content, fmu_submodule and surface(name) on Sumo.
        Return list of tuples (realization, realization)
        """
        url = (
            f"{self.api.base_url}/search?"
            f"$query=class:surface AND "
            f"_sumo.parent_object:{parent} AND "
            f"data.content.keyword:{content} AND "
            f"fmu.iteration.name:{iteration} AND "
            f"data.name:{surface}"
        )
        # print("Sumo:get_realizations ", url)
        response = self.api.callAzureApi.get_json(url=url)
        hits = [hit for hit in response.get("hits").get("hits")]
        import json

        return [
            hit.get("_source").get("fmu").get("realization").get("id")
            for hit in hits
            if hit.get("_source").get("fmu").get("realization") is not None
        ]

    def get_surface(self, parent, iteration, content, surface, realization):
        """Get a specific surface from Sumo by its object_id,
        return as xtgeo.RegularSurface object"""
        url = (
            f"{self.api.base_url}/search?"
            f"$query=class:surface AND "
            f"_sumo.parent_object:{parent} AND "
            f"data.content.keyword:{content} AND "
            f"fmu.iteration.name:{iteration} AND "
            f"data.name:{surface} AND "
            f"fmu.realization.id:{realization}"
        )
        response = self.api.callAzureApi.get_json(url=url)
        hits = [hit for hit in response.get("hits").get("hits")]
        if len(hits) == 1:
            object_id = hits[0].get("_id")
        bytestring = self.api.get_blob(object_id)
        surface = xtgeo.RegularSurface().from_file(
            io.BytesIO(bytestring), fformat="irap_binary"
        )
        return surface

    def get_metadata(self, object_id):
        print("get_metadata called with object_id: {}".format(object_id))
        metadata = self.api.get_json(object_id=object_id)

        print("returning metadata")

        return metadata

    def report_time_elapsed(self, title, start, end, duration):
        print("==== " + title + " ====")
        print("Start: ", start)
        print("End: ", end)
        print("Duration: {} seconds".format(duration))
        print("====")


# api = CallSumoApi(env="fmu")
# s = _Sumo(api)
# s.api.get_bearer_token()
# case_id = s.get_cases()[0][1]
# iterations = s.get_iterations(case_id)
# contents = s.get_contents(case_id, iterations[0])
# for iteration in iterations:
#     print(iteration)
#     print(s.get_contents(case_id, iteration))
# surfaces = s.get_surfaces(case_id, iteration=iterations[0], content=contents[0])
# reals = s.get_realizations(
#     case_id, iteration=iterations[0], content=contents[0], surface=surfaces[0]
# )
# surface = s.get_surface(
#     case_id,
#     iteration=iterations[0],
#     content=contents[0],
#     surface=surfaces[0],
#     realization=reals[0],
# )
# print(surface)
