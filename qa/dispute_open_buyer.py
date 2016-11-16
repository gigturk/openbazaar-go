import requests
import json
import time
from collections import OrderedDict
from test_framework.test_framework import OpenBazaarTestFramework, TestFailure


class DisputeOpenBuyerTest(OpenBazaarTestFramework):

    def __init__(self):
        super().__init__()
        self.num_nodes = 3

    def run_test(self):
        alice = self.nodes[0]
        bob = self.nodes[1]
        charlie = self.nodes[2]

        # generate some coins and send them to bob
        time.sleep(4)
        api_url = bob["gateway_url"] + "wallet/address"
        r = requests.get(api_url)
        if r.status_code == 200:
            resp = json.loads(r.text)
            address = resp["address"]
        elif r.status_code == 404:
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Address endpoint not found")
        else:
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Unknown response")
        self.send_bitcoin_cmd("generatetoaddress", 1, address)
        time.sleep(2)
        self.send_bitcoin_cmd("generate", 125)
        time.sleep(3)

        # create a profile for charlie
        pro = {"name": "Charlie"}
        api_url = charlie["gateway_url"] + "ob/profile"
        r = requests.post(api_url, data=json.dumps(pro, indent=4))
        if r.status_code == 404:
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Profile post endpoint not found")
        elif r.status_code != 200:
            resp = json.loads(r.text)
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Profile POST failed. Reason: %s", resp["reason"])
        time.sleep(4)

        # make charlie a moderator
        with open('testdata/moderation.json') as listing_file:
            moderation_json = json.load(listing_file, object_pairs_hook=OrderedDict)
        api_url = charlie["gateway_url"] + "ob/moderator"
        r = requests.post(api_url, data=json.dumps(moderation_json, indent=4))
        if r.status_code == 404:
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Moderator post endpoint not found")
        elif r.status_code != 200:
            resp = json.loads(r.text)
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Moderator POST failed. Reason: %s", resp["reason"])
        moderatorId = charlie["peerId"]
        time.sleep(4)

        # post listing to alice
        with open('testdata/listing.json') as listing_file:
            listing_json = json.load(listing_file, object_pairs_hook=OrderedDict)

        api_url = alice["gateway_url"] + "ob/listing"
        r = requests.post(api_url, data=json.dumps(listing_json, indent=4))
        if r.status_code == 404:
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Listing post endpoint not found")
        elif r.status_code != 200:
            resp = json.loads(r.text)
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Listing POST failed. Reason: %s", resp["reason"])
        time.sleep(4)

        # get listing hash
        api_url = alice["gateway_url"] + "ipns/" + alice["peerId"] + "/listings/index.json"
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Couldn't get listing index")
        resp = json.loads(r.text)
        listingId = resp[0]["hash"]

        # bob send order
        with open('testdata/order_direct.json') as order_file:
            order_json = json.load(order_file, object_pairs_hook=OrderedDict)
        order_json["items"][0]["listingHash"] = listingId
        order_json["moderator"] = moderatorId
        api_url = bob["gateway_url"] + "ob/purchase"
        r = requests.post(api_url, data=json.dumps(order_json, indent=4))
        if r.status_code == 404:
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Purchase post endpoint not found")
        elif r.status_code != 200:
            resp = json.loads(r.text)
            self.print_logs(alice, "ob.log")
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Purchase POST failed. Reason: %s", resp["reason"])
        resp = json.loads(r.text)
        orderId = resp["orderId"]
        payment_address = resp["paymentAddress"]
        payment_amount = resp["amount"]

        # check the purchase saved correctly
        api_url = bob["gateway_url"] + "ob/order/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Couldn't load order from Bob")
        resp = json.loads(r.text)
        if resp["state"] != "CONFIRMED":
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Bob purchase saved in incorrect state")
        if resp["funded"] == True:
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Bob incorrectly saved as funded")

        # check the sale saved correctly
        api_url = alice["gateway_url"] + "ob/order/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Couldn't load order from Alice")
        resp = json.loads(r.text)
        if resp["state"] != "CONFIRMED":
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Alice purchase saved in incorrect state")
        if resp["funded"] == True:
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Alice incorrectly saved as funded")

        # fund order
        spend = {
            "address": payment_address,
            "amount": payment_amount,
            "feeLevel": "NORMAL"
        }
        api_url = bob["gateway_url"] + "wallet/spend"
        r = requests.post(api_url, data=json.dumps(spend, indent=4))
        if r.status_code == 404:
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Spend post endpoint not found")
        elif r.status_code != 200:
            resp = json.loads(r.text)
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Spend POST failed. Reason: %s", resp["reason"])
        time.sleep(12)

        # check bob detected payment
        api_url = bob["gateway_url"] + "ob/order/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Couldn't load order from Bob")
        resp = json.loads(r.text)
        if resp["state"] != "FUNDED":
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Bob failed to detect his payment")
        if resp["funded"] == False:
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Bob incorrectly saved as unfunded")

        # check alice detected payment
        api_url = alice["gateway_url"] + "ob/order/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Couldn't load order from Alice")
        resp = json.loads(r.text)
        if resp["state"] != "FUNDED":
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Alice failed to detect payment")
        if resp["funded"] == False:
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Alice incorrectly saved as unfunded")
        
        # Bob open dispute
        dispute = {
            "orderId": orderId,
            "claim": "Bastard ripped me off"
        }
        api_url = bob["gateway_url"] + "ob/opendispute/"
        r = requests.post(api_url, data=json.dumps(dispute, indent=4))
        if r.status_code == 404:
            raise TestFailure("DisputeOpenBuyerTest - FAIL: OpenDispute post endpoint not found")
        elif r.status_code != 200:
            resp = json.loads(r.text)
            raise TestFailure("DisputeOpenBuyerTest - FAIL: OpenDispute POST failed. Reason: %s", resp["reason"])
        time.sleep(4)

        # Bob check dispute opened correctly
        api_url = bob["gateway_url"] + "ob/order/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Couldn't load order from Bob")
        resp = json.loads(r.text)
        if resp["state"] != "DISPUTED":
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Bob failed to detect his dispute")

        # Alice check dispute opened correctly
        api_url = alice["gateway_url"] + "ob/order/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Couldn't load order from Alice")
        resp = json.loads(r.text)
        if resp["state"] != "DISPUTED":
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Alice failed to detect the dispute")

        # Charlie check dispute opened correctly
        api_url = charlie["gateway_url"] + "ob/case/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Couldn't load case from Clarlie")
        resp = json.loads(r.text)
        if resp["state"] != "DISPUTED":
            raise TestFailure("DisputeOpenBuyerTest - FAIL: Charlie failed to detect the dispute")

        print("DisputeOpenBuyerTest - PASS")

if __name__ == '__main__':
    print("Running DisputeOpenBuyerTest")
    DisputeOpenBuyerTest().main(["--regtest", "--disableexchangerates"])
