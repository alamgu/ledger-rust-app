import pytest
import concurrent.futures
import time

from application_client.boilerplate_transaction import Transaction
from application_client.boilerplate_command_sender import BoilerplateCommandSender, Errors
from application_client.boilerplate_response_unpacker import unpack_get_public_key_response, unpack_sign_tx_response
from ragger.error import ExceptionRAPDU
from ragger.navigator import NavIns, NavInsID
from utils import ROOT_SCREENSHOT_PATH, check_signature_validity

def test_sign_tx_short_tx(backend, scenario_navigator, firmware, navigator):
    # Use the app interface instead of raw interface
    client = BoilerplateCommandSender(backend)
    # The path used for this entire test
    path = "m/44'/535348'/0'"

    _, public_key, _, _ = client.get_public_key(path=path)

    transaction="smalltx".encode('utf-8')

    def apdu_task():
        return client.sign_tx(path=path, transaction=transaction)

    def nav_task():
        navigator.navigate_and_compare(
            instructions=[NavInsID.RIGHT_CLICK, NavInsID.RIGHT_CLICK, NavInsID.RIGHT_CLICK, NavInsID.RIGHT_CLICK, NavInsID.BOTH_CLICK]
            , timeout=10
            , path=scenario_navigator.screenshot_path
            , test_case_name="test_sign_tx_short_tx"
            , screen_change_before_first_instruction=False
            , screen_change_after_last_instruction=False
        )

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(apdu_task)
        # This delay is necessary, otherwise the test hangs
        time.sleep(2)
        executor.submit(nav_task)

        der_sig = future.result()
        assert len(der_sig) == 64
        # assert check_signature_validity(public_key, der_sig, transaction)

def test_sign_tx_long_tx(backend, scenario_navigator, firmware, navigator):
    # Use the app interface instead of raw interface
    client = BoilerplateCommandSender(backend)
    path = "m/44'/535348'/0'"

    _, public_key, _, _ = client.get_public_key(path=path)

    transaction=("looongtx" * 100).encode('utf-8')

    def apdu_task():
        return client.sign_tx(path=path, transaction=transaction)

    def nav_task():
        navigator.navigate_and_compare(
            instructions=[NavInsID.RIGHT_CLICK, NavInsID.RIGHT_CLICK, NavInsID.RIGHT_CLICK, NavInsID.RIGHT_CLICK, NavInsID.BOTH_CLICK]
            , timeout=10
            , path=scenario_navigator.screenshot_path
            , test_case_name="test_sign_tx_long_tx"
            , screen_change_before_first_instruction=False
            , screen_change_after_last_instruction=False
        )

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(apdu_task)
        # This delay is necessary, otherwise the test hangs
        time.sleep(2)
        executor.submit(nav_task)

        der_sig = future.result()
        assert len(der_sig) == 64
        # assert check_signature_validity(public_key, der_sig, transaction)


# Transaction signature refused test
# The test will ask for a transaction signature that will be refused on screen
def test_sign_tx_refused(backend, scenario_navigator, firmware, navigator):
    pytest.skip()
    # Use the app interface instead of raw interface
    client = BoilerplateCommandSender(backend)
    path = "m/44'/535348'/0'"

    transaction=("looongtx" * 100).encode('utf-8')

    with pytest.raises(ExceptionRAPDU) as e:
        with client.sign_tx(path=path, transaction=transaction):
            navigator.navigate_and_compare(
                instructions=[NavInsID.RIGHT_CLICK, NavInsID.RIGHT_CLICK, NavInsID.RIGHT_CLICK, NavInsID.RIGHT_CLICK, NavInsID.RIGHT_CLICK, NavInsID.BOTH_CLICK]
                , timeout=10
                , path=scenario_navigator.screenshot_path
                , test_case_name="test_sign_tx_long_tx"
                , screen_change_before_first_instruction=False
                , screen_change_after_last_instruction=False
            )
    
    # Assert that we have received a refusal
    # assert e.value.status == Errors.SW_DENY
    assert len(e.value.data) == 0

def toggle_blind_sign(navigator):
    navigator.navigate(
        instructions=[NavInsID.RIGHT_CLICK, NavInsID.RIGHT_CLICK, NavInsID.BOTH_CLICK, NavInsID.BOTH_CLICK, NavInsID.RIGHT_CLICK, NavInsID.BOTH_CLICK, NavInsID.LEFT_CLICK, NavInsID.LEFT_CLICK]
        , timeout=10
        , screen_change_before_first_instruction=False
    )
