from datetime import datetime
from unittest.mock import patch

import pytest
from freezegun import freeze_time

from local_providers import AllocineStocks
from local_providers.allocine_stocks import retrieve_movie_information, _parse_movie_duration
from models import PcObject, Offer, EventType, Product
from repository.provider_queries import get_provider_by_local_class
from tests.conftest import clean_database
from tests.test_utils import create_offerer, create_venue, create_venue_provider, create_product_with_event_type, \
    create_offer_with_event_product


class AllocineStocksTest:
    class InitTest:
        @patch('local_providers.allocine_stocks.get_movies_showtimes')
        @patch.dict('os.environ', {'ALLOCINE_API_KEY': 'token'})
        @clean_database
        def test_should_call_allocine_api(self, mock_call_allocine_api, app):
            # Given
            theater_token = 'test'

            offerer = create_offerer(siren='775671464')
            venue = create_venue(offerer, name='Cinéma Allociné', siret='77567146400110')
            PcObject.save(venue)

            allocine_provider = get_provider_by_local_class('AllocineStocks')
            venue_provider = create_venue_provider(venue, allocine_provider, venue_id_at_offer_provider=theater_token)
            PcObject.save(venue_provider)

            # When
            AllocineStocks(venue_provider)

            # Then
            mock_call_allocine_api.assert_called_once_with('token', theater_token)

    class NextTest:
        @patch('local_providers.allocine_stocks.get_movies_showtimes')
        @patch.dict('os.environ', {'ALLOCINE_API_KEY': 'token'})
        @freeze_time('2019-10-15 09:00:00')
        @clean_database
        def test_should_return_providable_infos_for_each_movie(self, mock_call_allocine_api, app):
            # Given
            theater_token = 'test'
            mock_call_allocine_api.return_value = iter([
                {
                    "node": {
                        "movie": {
                            "id": "TW92aWU6Mzc4MzI=",
                            "internalId": 37832,
                            "backlink": {
                                "url": r"http:\/\/www.allocine.fr\/film\/fichefilm_gen_cfilm=37832.html",
                                "label": "Tous les d\u00e9tails du film sur AlloCin\u00e9"
                            },
                            "data": {
                                "eidr": r"10.5240\/EF0C-7FB2-7D20-46D1-5C8D-E",
                                "productionYear": 2001
                            },
                            "title": "Les Contes de la m\u00e8re poule",
                            "originalTitle": "Les Contes de la m\u00e8re poule",
                            "runtime": "PT0H46M0S",
                            "poster": {
                                "url": r"https:\/\/fr.web.img6.acsta.net\/medias\/nmedia\/00\/02\/32\/64\/69215979_af.jpg"
                            },
                            "synopsis": "synopsis du film",
                            "releases": [
                                {
                                    "name": "Released",
                                    "releaseDate": {
                                        "date": "2001-10-03"
                                    },
                                    "data": {
                                        "visa_number": "2009993528"
                                    }
                                }
                            ],
                            "credits": {
                                "edges": [
                                    {
                                        "node": {
                                            "person": {
                                                "firstName": "Farkhondeh",
                                                "lastName": "Torabi"
                                            },
                                            "position": {
                                                "name": "DIRECTOR"
                                            }
                                        }
                                    }
                                ]
                            },
                            "cast": {
                                "backlink": {
                                    "url": r"http:\/\/www.allocine.fr\/film\/fichefilm-255951\/casting\/",
                                    "label": "Casting complet du film sur AlloCin\u00e9"
                                },
                                "edges": []
                            },
                            "countries": [
                                {
                                    "name": "Iran",
                                    "alpha3": "IRN"
                                }
                            ],
                            "genres": [
                                "ANIMATION",
                                "FAMILY"
                            ],
                            "companies": []
                        },
                        "showtimes": [
                            {
                                "startsAt": "2019-10-29T10:30:00",
                                "diffusionVersion": "DUBBED"
                            }
                        ]
                    }
                }
            ])

            offerer = create_offerer(siren='775671464')
            venue = create_venue(offerer, name='Cinema Allocine', siret='77567146400110', booking_email='toto@toto.com')
            PcObject.save(venue)

            allocine_provider = get_provider_by_local_class('AllocineStocks')
            venue_provider = create_venue_provider(venue, allocine_provider, venue_id_at_offer_provider=theater_token)
            PcObject.save(venue_provider)

            allocine_stocks_provider = AllocineStocks(venue_provider)

            # When
            allocine_providable_infos = next(allocine_stocks_provider)

            # Then
            assert len(allocine_providable_infos) == 2

            product_providable_info = allocine_providable_infos[0]
            offer_providable_info = allocine_providable_infos[1]

            assert product_providable_info.type == Product
            assert product_providable_info.id_at_providers == 'TW92aWU6Mzc4MzI='
            assert product_providable_info.date_modified_at_provider == datetime(year=2019, month=10, day=15, hour=9)

            assert offer_providable_info.type == Offer
            assert offer_providable_info.id_at_providers == 'TW92aWU6Mzc4MzI='
            assert offer_providable_info.date_modified_at_provider == datetime(year=2019, month=10, day=15, hour=9)

    class UpdateObjectsTest:
        @patch('local_providers.allocine_stocks.get_movies_showtimes')
        @patch.dict('os.environ', {'ALLOCINE_API_KEY': 'token'})
        @clean_database
        def test_should_create_one_product_and_one_offer_with_movie_info(self, mock_call_allocine_api, app):
            # Given
            theater_token = 'test'
            mock_call_allocine_api.return_value = iter([
                {
                    "node": {
                        "movie": {
                            "id": "TW92aWU6Mzc4MzI=",
                            "internalId": 37832,
                            "backlink": {
                                "url": r"http:\/\/www.allocine.fr\/film\/fichefilm_gen_cfilm=37832.html",
                                "label": "Tous les d\u00e9tails du film sur AlloCin\u00e9"
                            },
                            "data": {
                                "eidr": r"10.5240\/EF0C-7FB2-7D20-46D1-5C8D-E",
                                "productionYear": 2001
                            },
                            "title": "Les Contes de la m\u00e8re poule",
                            "originalTitle": "Les Contes de la m\u00e8re poule",
                            "runtime": "PT0H46M0S",
                            "poster": {
                                "url": r"https:\/\/fr.web.img6.acsta.net\/medias\/nmedia\/00\/02\/32\/64\/69215979_af.jpg"
                            },
                            "synopsis": "synopsis du film",
                            "releases": [
                                {
                                    "name": "Released",
                                    "releaseDate": {
                                        "date": "2001-10-03"
                                    },
                                    "data": {
                                        "visa_number": "2009993528"
                                    }
                                }
                            ],
                            "credits": {
                                "edges": [
                                    {
                                        "node": {
                                            "person": {
                                                "firstName": "Farkhondeh",
                                                "lastName": "Torabi"
                                            },
                                            "position": {
                                                "name": "DIRECTOR"
                                            }
                                        }
                                    }
                                ]
                            },
                            "cast": {
                                "backlink": {
                                    "url": r"http:\/\/www.allocine.fr\/film\/fichefilm-255951\/casting\/",
                                    "label": "Casting complet du film sur AlloCin\u00e9"
                                },
                                "edges": []
                            },
                            "countries": [
                                {
                                    "name": "Iran",
                                    "alpha3": "IRN"
                                }
                            ],
                            "genres": [
                                "ANIMATION",
                                "FAMILY"
                            ],
                            "companies": []
                        },
                        "showtimes": [
                            {
                                "startsAt": "2019-10-29T10:30:00",
                                "diffusionVersion": "DUBBED"
                            }
                        ]
                    }
                }])

            offerer = create_offerer(siren='775671464')
            venue = create_venue(offerer, name='Cinema Allocine', siret='77567146400110', booking_email='toto@toto.com')
            PcObject.save(venue)

            allocine_provider = get_provider_by_local_class('AllocineStocks')
            allocine_provider.isActive = True
            venue_provider = create_venue_provider(venue, allocine_provider, venue_id_at_offer_provider=theater_token)
            PcObject.save(venue_provider)

            allocine_stocks_provider = AllocineStocks(venue_provider)

            # When
            allocine_stocks_provider.updateObjects()

            # Then
            created_offer = Offer.query.one()
            created_product = Product.query.one()

            assert created_offer.bookingEmail == 'toto@toto.com'
            assert created_offer.description == "synopsis du film\nhttp://www.allocine.fr/film/fichefilm_gen_cfilm=37832.html"
            assert created_offer.durationMinutes == 46
            assert created_offer.extraData["visa"] == "2009993528"
            assert created_offer.extraData["stageDirector"] == "Farkhondeh Torabi"
            assert created_offer.isDuo
            assert created_offer.name == "Les Contes de la mère poule"
            assert created_offer.product == created_product
            assert created_offer.type == str(EventType.CINEMA)

            assert created_product.description == "synopsis du film\nhttp://www.allocine.fr/film/fichefilm_gen_cfilm=37832.html"
            assert created_product.durationMinutes == 46
            assert created_product.extraData["visa"] == "2009993528"
            assert created_product.extraData["stageDirector"] == "Farkhondeh Torabi"
            assert created_product.name == "Les Contes de la mère poule"
            assert created_product.type == str(EventType.CINEMA)

        @patch('local_providers.allocine_stocks.get_movies_showtimes')
        @patch.dict('os.environ', {'ALLOCINE_API_KEY': 'token'})
        @clean_database
        def test_should_update_existing_product_duration_and_update_matching_offer(self, mock_call_allocine_api, app):
            # Given

            theater_token = 'test'
            mock_call_allocine_api.return_value = iter([
                {
                    "node": {
                        "movie": {
                            "id": "TW92aWU6Mzc4MzI=",
                            "internalId": 37832,
                            "backlink": {
                                "url": r"http:\/\/www.allocine.fr\/film\/fichefilm_gen_cfilm=37832.html",
                                "label": "Tous les d\u00e9tails du film sur AlloCin\u00e9"
                            },
                            "data": {
                                "eidr": r"10.5240\/EF0C-7FB2-7D20-46D1-5C8D-E",
                                "productionYear": 2001
                            },
                            "title": "Les Contes de la m\u00e8re poule",
                            "originalTitle": "Les Contes de la m\u00e8re poule",
                            "runtime": "PT1H50M0S",
                            "poster": {
                                "url": r"https:\/\/fr.web.img6.acsta.net\/medias\/nmedia\/00\/02\/32\/64\/69215979_af.jpg"
                            },
                            "synopsis": "synopsis du film",
                            "releases": [
                                {
                                    "name": "Released",
                                    "releaseDate": {
                                        "date": "2001-10-03"
                                    },
                                    "data": {
                                        "visa_number": "2009993528"
                                    }
                                }
                            ],
                            "credits": {
                                "edges": [
                                    {
                                        "node": {
                                            "person": {
                                                "firstName": "Farkhondeh",
                                                "lastName": "Torabi"
                                            },
                                            "position": {
                                                "name": "DIRECTOR"
                                            }
                                        }
                                    }
                                ]
                            },
                            "cast": {
                                "backlink": {
                                    "url": r"http:\/\/www.allocine.fr\/film\/fichefilm-255951\/casting\/",
                                    "label": "Casting complet du film sur AlloCin\u00e9"
                                },
                                "edges": []
                            },
                            "countries": [
                                {
                                    "name": "Iran",
                                    "alpha3": "IRN"
                                }
                            ],
                            "genres": [
                                "ANIMATION",
                                "FAMILY"
                            ],
                            "companies": []
                        },
                        "showtimes": [
                            {
                                "startsAt": "2019-10-29T10:30:00",
                                "diffusionVersion": "DUBBED"
                            }
                        ]
                    }
                }])

            product = create_product_with_event_type(
                event_name='Test event',
                event_type=EventType.CINEMA,
                duration_minutes=60,
                id_at_providers="TW92aWU6Mzc4MzI="
            )

            offerer = create_offerer(siren='775671464')
            venue = create_venue(offerer, name='Cinéma Allociné', siret='77567146400110', booking_email='toto@toto.com')

            offer = create_offer_with_event_product(product=product, event_name='Test event',
                                                    event_type=EventType.CINEMA,
                                                    duration_minutes=60,
                                                    id_at_providers="TW92aWU6Mzc4MzI=", venue=venue)
            PcObject.save(venue, product, offer)

            allocine_provider = get_provider_by_local_class('AllocineStocks')
            allocine_provider.isActive = True
            venue_provider = create_venue_provider(venue, allocine_provider, venue_id_at_offer_provider=theater_token)
            PcObject.save(venue_provider)

            allocine_stocks_provider = AllocineStocks(venue_provider)

            # When
            allocine_stocks_provider.updateObjects()

            # Then
            existing_offer = Offer.query.one()
            existing_product = Product.query.one()

            assert existing_offer.durationMinutes == 110
            assert existing_product.durationMinutes == 110

        @patch('local_providers.allocine_stocks.get_movies_showtimes')
        @patch.dict('os.environ', {'ALLOCINE_API_KEY': 'token'})
        @clean_database
        def test_should_update_existing_product_duration_and_create_new_offer_when_no_offer_exists(self,
                                                                                                   mock_call_allocine_api,
                                                                                                   app):
            # Given
            theater_token = 'test'
            mock_call_allocine_api.return_value = iter([
                {
                    "node": {
                        "movie": {
                            "id": "TW92aWU6Mzc4MzI=",
                            "internalId": 37832,
                            "backlink": {
                                "url": r"http:\/\/www.allocine.fr\/film\/fichefilm_gen_cfilm=37832.html",
                                "label": "Tous les d\u00e9tails du film sur AlloCin\u00e9"
                            },
                            "data": {
                                "eidr": r"10.5240\/EF0C-7FB2-7D20-46D1-5C8D-E",
                                "productionYear": 2001
                            },
                            "title": "Les Contes de la m\u00e8re poule",
                            "originalTitle": "Les Contes de la m\u00e8re poule",
                            "runtime": "PT1H50M0S",
                            "poster": {
                                "url": r"https:\/\/fr.web.img6.acsta.net\/medias\/nmedia\/00\/02\/32\/64\/69215979_af.jpg"
                            },
                            "synopsis": "synopsis du film",
                            "releases": [
                                {
                                    "name": "Released",
                                    "releaseDate": {
                                        "date": "2001-10-03"
                                    },
                                    "data": {
                                        "visa_number": "2009993528"
                                    }
                                }
                            ],
                            "credits": {
                                "edges": [
                                    {
                                        "node": {
                                            "person": {
                                                "firstName": "Farkhondeh",
                                                "lastName": "Torabi"
                                            },
                                            "position": {
                                                "name": "DIRECTOR"
                                            }
                                        }
                                    }
                                ]
                            },
                            "cast": {
                                "backlink": {
                                    "url": r"http:\/\/www.allocine.fr\/film\/fichefilm-255951\/casting\/",
                                    "label": "Casting complet du film sur AlloCin\u00e9"
                                },
                                "edges": []
                            },
                            "countries": [
                                {
                                    "name": "Iran",
                                    "alpha3": "IRN"
                                }
                            ],
                            "genres": [
                                "ANIMATION",
                                "FAMILY"
                            ],
                            "companies": []
                        },
                        "showtimes": [
                            {
                                "startsAt": "2019-10-29T10:30:00",
                                "diffusionVersion": "DUBBED"
                            }
                        ]
                    }
                }])

            product = create_product_with_event_type(
                event_name='Test event',
                event_type=EventType.CINEMA,
                duration_minutes=60,
                id_at_providers="TW92aWU6Mzc4MzI="
            )

            offerer = create_offerer(siren='775671464')
            venue = create_venue(offerer, name='Cinema Allocine', siret='77567146400110', booking_email='toto@toto.com')
            PcObject.save(venue, product)

            allocine_provider = get_provider_by_local_class('AllocineStocks')
            allocine_provider.isActive = True
            venue_provider = create_venue_provider(venue, allocine_provider, venue_id_at_offer_provider=theater_token)
            PcObject.save(venue_provider)

            allocine_stocks_provider = AllocineStocks(venue_provider)

            # When
            allocine_stocks_provider.updateObjects()

            # Then
            created_offer = Offer.query.one()
            existing_product = Product.query.one()

            assert existing_product.durationMinutes == 110
            assert created_offer.type == str(EventType.CINEMA)
            assert created_offer.name == 'Les Contes de la mère poule'

        @patch('local_providers.allocine_stocks.get_movies_showtimes')
        @patch.dict('os.environ', {'ALLOCINE_API_KEY': 'token'})
        @clean_database
        def test_should_create_product_and_new_offer_with_missing_visa_and_stage_director(self,
                                                                                          mock_call_allocine_api,
                                                                                          app):
            # Given
            theater_token = 'test'
            mock_call_allocine_api.return_value = iter([
                {
                    "node": {
                        "movie": {
                            "id": "TW92aWU6Mzc4MzI=",
                            "internalId": 37832,
                            "backlink": {
                                "url": r"http:\/\/www.allocine.fr\/film\/fichefilm_gen_cfilm=37832.html",
                                "label": "Tous les d\u00e9tails du film sur AlloCin\u00e9"
                            },
                            "data": {
                                "eidr": r"10.5240\/EF0C-7FB2-7D20-46D1-5C8D-E",
                                "productionYear": 2001
                            },
                            "title": "Les Contes de la m\u00e8re poule",
                            "originalTitle": "Les Contes de la m\u00e8re poule",
                            "runtime": "PT1H50M0S",
                            "poster": {
                                "url": r"https:\/\/fr.web.img6.acsta.net\/medias\/nmedia\/00\/02\/32\/64\/69215979_af.jpg"
                            },
                            "synopsis": "synopsis du film",
                            "releases": [
                                {
                                    "name": "Released",
                                    "releaseDate": {
                                        "date": "2001-10-03"
                                    },
                                    "data": []
                                }
                            ],
                            "credits": {
                                "edges": []
                            },
                            "cast": {
                                "backlink": {
                                    "url": r"http:\/\/www.allocine.fr\/film\/fichefilm-255951\/casting\/",
                                    "label": "Casting complet du film sur AlloCin\u00e9"
                                },
                                "edges": []
                            },
                            "countries": [
                                {
                                    "name": "Iran",
                                    "alpha3": "IRN"
                                }
                            ],
                            "genres": [
                                "ANIMATION",
                                "FAMILY"
                            ],
                            "companies": []
                        },
                        "showtimes": [
                            {
                                "startsAt": "2019-10-29T10:30:00",
                                "diffusionVersion": "DUBBED"
                            }
                        ]
                    }
                }])

            offerer = create_offerer(siren='775671464')
            venue = create_venue(offerer, name='Cinema Allocine', siret='77567146400110', booking_email='toto@toto.com')
            PcObject.save(venue)

            allocine_provider = get_provider_by_local_class('AllocineStocks')
            allocine_provider.isActive = True
            venue_provider = create_venue_provider(venue, allocine_provider, venue_id_at_offer_provider=theater_token)
            PcObject.save(venue_provider)

            allocine_stocks_provider = AllocineStocks(venue_provider)

            # When
            allocine_stocks_provider.updateObjects()

            # Then
            created_offer = Offer.query.one()
            created_product = Product.query.one()

            assert created_product.durationMinutes == 110
            assert created_product.extraData == {}
            assert created_offer.extraData == {}
            assert created_offer.type == str(EventType.CINEMA)
            assert created_offer.name == 'Les Contes de la mère poule'


class ParseMovieDurationTest:
    def test_should_convert_duration_string_to_minutes(self):
        # Given
        movie_runtime = "PT1H50M0S"

        # When
        duration_in_minutes = _parse_movie_duration(movie_runtime)

        # Then
        assert duration_in_minutes == 110

    def test_should_only_parse_hours_and_minutes(self):
        # Given
        movie_runtime = "PT11H0M15S"

        # When
        duration_in_minutes = _parse_movie_duration(movie_runtime)

        # Then
        assert duration_in_minutes == 660

    def test_should_return_None_when_null_value_given(self):
        # Given
        movie_runtime = None

        # When
        duration_in_minutes = _parse_movie_duration(movie_runtime)

        # Then
        assert not duration_in_minutes


class RetrieveMovieInformationTest:
    def test_should_retrieve_information_from_wanted_json_nodes(self):
        # Given
        movie_information = {
            "node": {
                "movie": {
                    "id": "TW92aWU6Mzc4MzI=",
                    "internalId": 37832,
                    "backlink": {
                        "url": r"http:\/\/www.allocine.fr\/film\/fichefilm_gen_cfilm=37832.html",
                        "label": "Tous les d\u00e9tails du film sur AlloCin\u00e9"
                    },
                    "data": {
                        "eidr": r"10.5240\/EF0C-7FB2-7D20-46D1-5C8D-E",
                        "productionYear": 2001
                    },
                    "title": "Les Contes de la m\u00e8re poule",
                    "originalTitle": "Les Contes de la m\u00e8re poule",
                    "runtime": "PT1H50M0S",
                    "poster": {
                        "url": r"https:\/\/fr.web.img6.acsta.net\/medias\/nmedia\/00\/02\/32\/64\/69215979_af.jpg"
                    },
                    "synopsis": "synopsis du film",
                    "releases": [
                        {
                            "name": "Released",
                            "releaseDate": {
                                "date": "2001-10-03"
                            },
                            "data": {
                                "visa_number": "2009993528"
                            }
                        }
                    ],
                    "credits": {
                        "edges": [
                            {
                                "node": {
                                    "person": {
                                        "firstName": "Farkhondeh",
                                        "lastName": "Torabi"
                                    },
                                    "position": {
                                        "name": "DIRECTOR"
                                    }
                                }
                            }
                        ]
                    },
                    "cast": {
                        "backlink": {
                            "url": r"http:\/\/www.allocine.fr\/film\/fichefilm-255951\/casting\/",
                            "label": "Casting complet du film sur AlloCin\u00e9"
                        },
                        "edges": []
                    },
                    "countries": [
                        {
                            "name": "Iran",
                            "alpha3": "IRN"
                        }
                    ],
                    "genres": [
                        "ANIMATION",
                        "FAMILY"
                    ],
                    "companies": []
                },
                "showtimes": [
                    {
                        "startsAt": "2019-10-29T10:30:00",
                        "diffusionVersion": "DUBBED"
                    }
                ]
            }
        }

        # When
        movie_parsed_information = retrieve_movie_information(movie_information['node']['movie'])

        # Then
        assert movie_parsed_information['title'] == "Les Contes de la mère poule"
        assert movie_parsed_information[
                   'description'] == "synopsis du film\nhttp://www.allocine.fr/film/fichefilm_gen_cfilm=37832.html"
        assert movie_parsed_information["visa"] == "2009993528"
        assert movie_parsed_information["stageDirector"] == "Farkhondeh Torabi"
        assert movie_parsed_information['duration'] == 110

    def test_should_not_add_operating_visa_and_stageDirector_keys_when_nodes_are_missing(self):
        # Given
        movie_information = {
            "node": {
                "movie": {
                    "id": "TW92aWU6Mzc4MzI=",
                    "internalId": 37832,
                    "backlink": {
                        "url": r"http:\/\/www.allocine.fr\/film\/fichefilm_gen_cfilm=37832.html",
                        "label": "Tous les d\u00e9tails du film sur AlloCin\u00e9"
                    },
                    "data": {
                        "eidr": r"10.5240\/EF0C-7FB2-7D20-46D1-5C8D-E",
                        "productionYear": 2001
                    },
                    "title": "Les Contes de la m\u00e8re poule",
                    "originalTitle": "Les Contes de la m\u00e8re poule",
                    "runtime": "PT1H50M0S",
                    "poster": {
                        "url": r"https:\/\/fr.web.img6.acsta.net\/medias\/nmedia\/00\/02\/32\/64\/69215979_af.jpg"
                    },
                    "synopsis": "synopsis du film",
                    "releases": [
                        {
                            "name": "Released",
                            "releaseDate": {
                                "date": "2019-11-20"
                            },
                            "data": []
                        }
                    ],
                    "credits": {
                        "edges": []
                    },
                    "cast": {
                        "backlink": {
                            "url": r"http:\/\/www.allocine.fr\/film\/fichefilm-255951\/casting\/",
                            "label": "Casting complet du film sur AlloCin\u00e9"
                        },
                        "edges": []
                    },
                    "countries": [
                        {
                            "name": "Iran",
                            "alpha3": "IRN"
                        }
                    ],
                    "genres": [
                        "ANIMATION",
                        "FAMILY"
                    ],
                    "companies": []
                },
                "showtimes": [
                    {
                        "startsAt": "2019-10-29T10:30:00",
                        "diffusionVersion": "DUBBED"
                    }
                ]
            }
        }

        # When
        movie_parsed_information = retrieve_movie_information(movie_information['node']['movie'])

        # Then
        assert movie_parsed_information['title'] == "Les Contes de la mère poule"
        assert movie_parsed_information[
                   'description'] == "synopsis du film\nhttp://www.allocine.fr/film/fichefilm_gen_cfilm=37832.html"
        assert "visa" not in movie_parsed_information
        assert "stageDirector" not in movie_parsed_information
        assert movie_parsed_information['duration'] == 110

    def test_should_raise_key_error_exception_when_missing_keys_in_movie_information(self):
        # Given
        movie_information = {
            'node': {
                'movie': {
                    "id": "TW92aWU6Mzc4MzI=",
                    "backlink": {
                        "url": r"http:\/\/www.allocine.fr\/film\/fichefilm_gen_cfilm=37832.html",
                        "label": "Tous les d\u00e9tails du film sur AlloCin\u00e9"
                    },
                    "title": "Les Contes de la m\u00e8re poule",
                }
            }
        }

        # When
        with pytest.raises(KeyError):
            retrieve_movie_information(movie_information['node']['movie'])