import pytest

from flight_tracker.domain import Airport
from flight_tracker.services.city_resolver import CityResolver, normalize

AIRPORTS = [
    Airport("FOR", "Pinto Martins International Airport", "Fortaleza", "BR", 3),
    Airport("GIG", "Rio de Janeiro Galeão – Tom Jobim International Airport", "Rio de Janeiro", "BR", 3),
    Airport("SDU", "Santos Dumont Airport", "Rio de Janeiro", "BR", 3),
    Airport("RBR", "Rio Branco International Airport", "Rio Branco", "BR", 3),
    Airport("SJP", "São José do Rio Preto Airport", "São José do Rio Preto", "BR", 2),
    Airport("NAT", "Greater Natal Airport, Rio Grande do Norte", "Natal", "BR", 3),
    Airport("RGL", "Piloto Civil Norberto Fernández Airport", "Rio Gallegos", "AR", 2),
    Airport("LIS", "Humberto Delgado Airport", "Lisbon", "PT", 3, "Lisboa, Portela"),
    Airport("MRO", "Mario Airport", "Marioville", "BR", 1),
]


@pytest.fixture
def resolver() -> CityResolver:
    return CityResolver(AIRPORTS)


def test_normalize_removes_accents_case_and_punctuation():
    assert normalize("  São-Paulo/Guarulhos ") == "sao paulo guarulhos"


def test_iata_code_resolves_directly(resolver):
    options = resolver.resolve("gig")

    assert [option.codes for option in options] == [("GIG",)]


def test_unique_city_resolves_to_single_option(resolver):
    options = resolver.resolve("fortaleza")

    assert len(options) == 1
    assert options[0].codes == ("FOR",)
    assert options[0].display == "Fortaleza (FOR)"


def test_ambiguous_query_lists_cities_by_relevance(resolver):
    labels = [option.label for option in resolver.resolve("Rio")]

    assert labels[0] == "Rio de Janeiro — todos (GIG, SDU)"
    assert labels[1].startswith("Rio de Janeiro (GIG)")
    assert labels[2].startswith("Rio de Janeiro (SDU)")
    assert labels[3] == "Rio Branco (RBR)"
    assert labels[4] == "Rio Gallegos, AR (RGL)"
    assert labels[5] == "São José do Rio Preto (SJP)"
    assert labels[-1] == "Natal (NAT)"


def test_word_prefix_only_avoids_matches_inside_words(resolver):
    codes = [option.codes for option in resolver.resolve("rio")]

    assert ("MRO",) not in codes


def test_multi_airport_city_offers_all_option(resolver):
    options = resolver.resolve("Rio de Janeiro")

    assert options[0].codes == ("GIG", "SDU")
    assert {option.codes for option in options[1:]} == {("GIG",), ("SDU",)}


def test_keywords_match_alternate_names(resolver):
    options = resolver.resolve("Lisboa")

    assert options[0].codes == ("LIS",)
    assert options[0].label == "Lisbon, PT (LIS)"


def test_airport_name_match(resolver):
    assert [option.codes for option in resolver.resolve("galeão")] == [("GIG",)]


def test_unknown_or_blank_returns_nothing(resolver):
    assert resolver.resolve("xyzabc") == []
    assert resolver.resolve("   ") == []


def test_options_are_capped():
    resolver = CityResolver(AIRPORTS, max_options=2)

    assert len(resolver.resolve("rio")) == 2


def test_bundled_dataset_loads_and_resolves_real_cities():
    resolver = CityResolver.from_csv()

    assert resolver.resolve("Fortaleza")[0].codes == ("FOR",)
    assert resolver.resolve("São Paulo")[0].codes == ("CGH", "GRU")
