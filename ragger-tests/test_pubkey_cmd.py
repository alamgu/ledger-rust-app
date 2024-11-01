import pytest
import concurrent.futures

from application_client.boilerplate_command_sender import BoilerplateCommandSender, Errors
from application_client.boilerplate_response_unpacker import unpack_get_public_key_response
from contextlib import contextmanager
from ragger.bip import calculate_public_key_and_chaincode, CurveChoice
from ragger.error import ExceptionRAPDU
from ragger.navigator import NavInsID, NavIns
from utils import ROOT_SCREENSHOT_PATH


# In this test we check that the GET_PUBLIC_KEY works in non-confirmation mode
def test_get_public_key_no_confirm(backend):
    pytest.skip("sss")
    for path in [ "m/44'/535348'/0'"]:
        client = BoilerplateCommandSender(backend)
        response = client.get_public_key(path=path).data
        _, public_key, _, _ = unpack_get_public_key_response(response)

        assert public_key.hex() == "19e2fea57e82293b4fee8120d934f0c5a4907198f8df29e9a153cfd7d9383488"


# In this test we check that the GET_PUBLIC_KEY works in confirmation mode
def test_get_public_key_confirm_accepted(backend, scenario_navigator):
    client = BoilerplateCommandSender(backend)
    path = "m/44'/535348'/0'"

    @contextmanager
    def runApdu():
        result = client.get_public_key_with_confirmation(path=path)
        # with
        return result

    with runApdu():
        scenario_navigator.address_review_approve()

    response = client.get_async_response().data
    _, public_key, _, _ = unpack_get_public_key_response(response)

    assert public_key.hex() == "19e2fea57e82293b4fee8120d934f0c5a4907198f8df29e9a153cfd7d9383488"


# # In this test we check that the GET_PUBLIC_KEY in confirmation mode replies an error if the user refuses
# def test_get_public_key_confirm_refused(backend, scenario_navigator):
#     client = BoilerplateCommandSender(backend)
#     path = "m/44'/535348'/0'"

#     with pytest.raises(ExceptionRAPDU) as e:
#         with client.get_public_key_with_confirmation(path=path):
#             scenario_navigator.address_review_reject()

#     # Assert that we have received a refusal
#     assert e.value.status == Errors.SW_DENY
#     assert len(e.value.data) == 0

# def test_get_public_key_confirm_accepted(backend, scenario_navigator):
#     client = BoilerplateCommandSender(backend)
#     path = "m/44'/535348'/0'"

#     with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
#         future = executor.submit(client.get_public_key_with_confirmation(path=path))
#         print("runInAsync 2")
#         future2 = executor.submit(scenario_navigator.address_review_approve())
#         print("runInAsync 3")
#         return future.result()
#     # await doasync
#     #     # Get the result when needed
#     #     result = future.result()
#     #     print(result)
#     # async def runInAsync():
#     #     print("start runInAsync")
#     #     doasync = asyncio.create_task(client.get_public_key_with_confirmation(path=path))
#     #     print("runInAsync 2")
#     #     scenario_navigator.address_review_approve()
#     #     print("runInAsync 3")
#     #     return await doasync

#     print("before runInAsync")
#     response = asyncio.run(runInAsync())
#     _, public_key, _, _ = unpack_get_public_key_response(response)

#     assert public_key.hex() == "19e2fea57e82293b4fee8120d934f0c5a4907198f8df29e9a153cfd7d9383488"
