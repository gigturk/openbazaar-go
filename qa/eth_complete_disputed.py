import requests
import json
import time
from collections import OrderedDict
from test_framework.test_framework import OpenBazaarTestFramework, TestFailure


class EthCompleteDisputedTest(OpenBazaarTestFramework):

    def __init__(self):
        super().__init__()
        self.num_nodes = 4

    def run_test(self):
        alice = self.nodes[1]
        bob = self.nodes[2]
        charlie = self.nodes[3]

        # check bob's initial balance
        time.sleep(4)
        api_url = bob["gateway_url"] + "wallet/balance/T" + self.cointype
        r = requests.get(api_url)
        if r.status_code == 200:
            resp = json.loads(r.text)
            bob_balance = int(resp["confirmed"])
        elif r.status_code == 404:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Address endpoint not found")
        else:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Unknown response")
        time.sleep(20)

        # create a profile for charlie
        pro = {"name": "Charlie"}
        api_url = charlie["gateway_url"] + "ob/profile"
        r = requests.post(api_url, data=json.dumps(pro, indent=4))
        if r.status_code == 404:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Profile post endpoint not found")
        elif r.status_code != 200:
            resp = json.loads(r.text)
            raise TestFailure("EthCompleteDisputedTest - FAIL: Profile POST failed. Reason: %s", resp["reason"])
        time.sleep(4)

        # make charlie a moderator
        with open('testdata/v5/moderation.json') as listing_file:
            moderation_json = json.load(listing_file, object_pairs_hook=OrderedDict)
        api_url = charlie["gateway_url"] + "ob/moderator"
        r = requests.put(api_url, data=json.dumps(moderation_json, indent=4))
        if r.status_code == 404:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Moderator post endpoint not found")
        elif r.status_code != 200:
            resp = json.loads(r.text)
            raise TestFailure("EthCompleteDisputedTest - FAIL: Moderator POST failed. Reason: %s", resp["reason"])
        moderatorId = charlie["peerId"]
        time.sleep(4)

        # post profile for alice
        with open('testdata/v5/profile.json') as profile_file:
            profile_json = json.load(profile_file, object_pairs_hook=OrderedDict)
        api_url = alice["gateway_url"] + "ob/profile"
        requests.post(api_url, data=json.dumps(profile_json, indent=4))

        # post listing to alice
        with open('testdata/v5/eth_listing.json') as listing_file:
            listing_json = json.load(listing_file, object_pairs_hook=OrderedDict)
        listing_json["item"]["priceCurrency"]["code"] = "T" + self.cointype
        listing_json["metadata"]["acceptedCurrencies"] = ["T" + self.cointype]
        listing_json["moderators"] = [moderatorId]
        api_url = alice["gateway_url"] + "ob/listing"
        r = requests.post(api_url, data=json.dumps(listing_json, indent=4))
        if r.status_code == 404:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Listing post endpoint not found")
        elif r.status_code != 200:
            resp = json.loads(r.text)
            raise TestFailure("EthCompleteDisputedTest - FAIL: Listing POST failed. Reason: %s", resp["reason"])
        resp = json.loads(r.text)
        slug = resp["slug"]
        time.sleep(4)

        # get listing hash
        api_url = alice["gateway_url"] + "ob/listings/" + alice["peerId"]
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Couldn't get listing index")
        resp = json.loads(r.text)
        listingId = resp[0]["hash"]

        # bob send order
        with open('testdata/v5/order_direct.json') as order_file:
            order_json = json.load(order_file, object_pairs_hook=OrderedDict)
        order_json["items"][0]["listingHash"] = listingId
        order_json["moderator"] = moderatorId
        order_json["paymentCoin"] = "T" + self.cointype
        api_url = bob["gateway_url"] + "ob/purchase"
        r = requests.post(api_url, data=json.dumps(order_json, indent=4))
        if r.status_code == 404:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Purchase post endpoint not found")
        elif r.status_code != 200:
            resp = json.loads(r.text)
            self.print_logs(alice, "ob.log")
            raise TestFailure("EthCompleteDisputedTest - FAIL: Purchase POST failed. Reason: %s", resp["reason"])
        resp = json.loads(r.text)
        orderId = resp["orderId"]
        payment_address = resp["paymentAddress"]
        payment_amount = resp["amount"]

        # check the purchase saved correctly
        api_url = bob["gateway_url"] + "ob/order/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Couldn't load order from Bob")
        resp = json.loads(r.text)
        if resp["state"] != "AWAITING_PAYMENT":
            raise TestFailure("EthCompleteDisputedTest - FAIL: Bob purchase saved in incorrect state")
        if resp["funded"] == True:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Bob incorrectly saved as funded")

        # check the sale saved correctly
        api_url = alice["gateway_url"] + "ob/order/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Couldn't load order from Alice")
        resp = json.loads(r.text)
        if resp["state"] != "AWAITING_PAYMENT":
            raise TestFailure("EthCompleteDisputedTest - FAIL: Alice purchase saved in incorrect state")
        if resp["funded"] == True:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Alice incorrectly saved as funded")

        # fund order
        spend = {
            "currencyCode": "T" + self.cointype,
            "address": payment_address,
            "amount": payment_amount["amount"],
            "feeLevel": "NORMAL",
            "requireAssociateOrder": True,
            "orderID": orderId
        }
        api_url = bob["gateway_url"] + "ob/orderspend"
        r = requests.post(api_url, data=json.dumps(spend, indent=4))
        if r.status_code == 404:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Spend post endpoint not found")
        elif r.status_code != 200:
            resp = json.loads(r.text)
            raise TestFailure("EthCompleteDisputedTest - FAIL: Spend POST failed. Reason: %s", resp["reason"])
        time.sleep(20)

        # check bob detected payment
        api_url = bob["gateway_url"] + "ob/order/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Couldn't load order from Bob")
        resp = json.loads(r.text)
        if resp["state"] != "AWAITING_FULFILLMENT":
            raise TestFailure("EthCompleteDisputedTest - FAIL: Bob failed to detect his payment")
        if resp["funded"] == False:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Bob incorrectly saved as unfunded")

        # check alice detected payment
        api_url = alice["gateway_url"] + "ob/order/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Couldn't load order from Alice")
        resp = json.loads(r.text)
        if resp["state"] != "AWAITING_FULFILLMENT":
            raise TestFailure("EthCompleteDisputedTest - FAIL: Alice failed to detect payment")
        if resp["funded"] == False:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Alice incorrectly saved as unfunded")

        # alice send order fulfillment
        with open('testdata/v5/fulfillment.json') as fulfillment_file:
            fulfillment_json = json.load(fulfillment_file, object_pairs_hook=OrderedDict)
        fulfillment_json["orderId"] = orderId
        fulfillment_json["slug"] = slug
        api_url = alice["gateway_url"] + "ob/orderfulfillment"
        r = requests.post(api_url, data=json.dumps(fulfillment_json, indent=4))
        if r.status_code == 404:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Fulfillment post endpoint not found")
        elif r.status_code != 200:
            resp = json.loads(r.text)
            raise TestFailure("EthCompleteDisputedTest - FAIL: Fulfillment POST failed. Reason: %s", resp["reason"])
        time.sleep(4)

        # Bob open dispute
        dispute = {
            "orderId": orderId,
            "claim": "Bastard ripped me off"
        }
        api_url = bob["gateway_url"] + "ob/opendispute/"
        r = requests.post(api_url, data=json.dumps(dispute, indent=4))
        if r.status_code == 404:
            raise TestFailure("EthCompleteDisputedTest - FAIL: OpenDispute post endpoint not found")
        elif r.status_code != 200:
            resp = json.loads(r.text)
            raise TestFailure("EthCompleteDisputedTest - FAIL: OpenDispute POST failed. Reason: %s", resp["reason"])
        time.sleep(4)

        # Bob check dispute opened correctly
        api_url = bob["gateway_url"] + "ob/order/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Couldn't load order from Bob")
        resp = json.loads(r.text)
        if resp["state"] != "DISPUTED":
            raise TestFailure("EthCompleteDisputedTest - FAIL: Bob failed to detect his dispute")

        # Alice check dispute opened correctly
        api_url = alice["gateway_url"] + "ob/order/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Couldn't load order from Alice")
        resp = json.loads(r.text)
        if resp["state"] != "DISPUTED":
            raise TestFailure("EthCompleteDisputedTest - FAIL: Alice failed to detect the dispute")

        # Charlie check dispute opened correctly
        api_url = charlie["gateway_url"] + "ob/case/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Couldn't load case from Clarlie")
        resp = json.loads(r.text, object_pairs_hook=OrderedDict)
        if resp["state"] != "DISPUTED":
            raise TestFailure("EthCompleteDisputedTest - FAIL: Charlie failed to detect the dispute")

        # Charlie close dispute
        dispute_resolution = {
            "OrderID": orderId,
            "Resolution": "I'm siding with Bob",
            "BuyerPercentage": 100,
            "VendorPercentage": 0
        }
        api_url = charlie["gateway_url"] + "ob/closedispute/"
        r = requests.post(api_url, data=json.dumps(dispute_resolution, indent=4))
        if r.status_code == 404:
            raise TestFailure("EthCompleteDisputedTest - FAIL: CloseDispute post endpoint not found")
        elif r.status_code != 200:
            resp = json.loads(r.text)
            raise TestFailure("EthCompleteDisputedTest - FAIL: CloseDispute POST failed. Reason: %s", resp["reason"])
        time.sleep(4)

        # Alice check dispute closed correctly
        api_url = alice["gateway_url"] + "ob/order/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Couldn't load order from Alice")
        resp = json.loads(r.text)
        if resp["state"] != "DECIDED":
            self.print_logs(alice, "ob.log")
            raise TestFailure("EthCompleteDisputedTest - FAIL: Alice failed to detect the dispute resolution")

        # Bob check dispute closed correctly
        api_url = bob["gateway_url"] + "ob/order/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Couldn't load order from Bob")
        resp = json.loads(r.text, object_pairs_hook=OrderedDict)
        if resp["state"] != "DECIDED":
            raise TestFailure("EthCompleteDisputedTest - FAIL: Bob failed to detect the dispute resolution")

        # Charlie check dispute closed correctly
        api_url = charlie["gateway_url"] + "ob/case/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Couldn't load case from Charlie")
        resp = json.loads(r.text, object_pairs_hook=OrderedDict)
        if resp["state"] != "RESOLVED":
            raise TestFailure("EthCompleteDisputedTest - FAIL: Charlie failed to detect the dispute resolution")

        # Bob release funds
        release = {
            "OrderID": orderId,
        }
        api_url = bob["gateway_url"] + "ob/releasefunds/"
        r = requests.post(api_url, data=json.dumps(release, indent=4))
        if r.status_code == 404:
            raise TestFailure("EthCompleteDisputedTest - FAIL: ReleaseFunds post endpoint not found")
        elif r.status_code != 200:
            resp = json.loads(r.text)
            raise TestFailure("EthCompleteDisputedTest - FAIL: ReleaseFunds POST failed. Reason: %s", resp["reason"])
        time.sleep(20)

        time.sleep(5)

        # Check bob received payout
        api_url = bob["gateway_url"] + "wallet/balance/T" + self.cointype
        r = requests.get(api_url)
        if r.status_code == 200:
            resp = json.loads(r.text)
            confirmed = int(resp["confirmed"])
            #unconfirmed = int(resp["unconfirmed"])
            #if confirmed <= (bob_balance) - int(payment_amount["amount"]):
            #    raise TestFailure("EthCompleteDisputedTest - FAIL: Bob failed to detect dispute payout")
        elif r.status_code == 404:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Receive coins endpoint not found")
        else:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Unknown response")

        # Bob check payout transaction recorded
        api_url = bob["gateway_url"] + "ob/order/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Couldn't load order from Bob")
        resp = json.loads(r.text, object_pairs_hook=OrderedDict)
        if len(resp["paymentAddressTransactions"]) != 2:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Bob failed to record payout transaction")
        if resp["state"] != "RESOLVED":
            raise TestFailure("EthCompleteDisputedTest - FAIL: Bob failed to set state to RESOLVED")

        # Alice check payout transaction recorded
        api_url = alice["gateway_url"] + "ob/order/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Couldn't load order from Alice")
        resp = json.loads(r.text, object_pairs_hook=OrderedDict)
        if len(resp["paymentAddressTransactions"]) != 2:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Alice failed to record payout transaction")
        if resp["state"] != "RESOLVED":
            raise TestFailure("EthCompleteDisputedTest - FAIL: Alice failed to set state to RESOLVED")

        # bob send order completion
        oc = {
            "orderId": orderId,
            "ratings": [
                {
                    "slug": slug,
                    "overall": 4,
                    "quality": 5,
                    "description": 5,
                    "customerService": 4,
                    "deliverySpeed": 3,
                    "Review": "I love it!"
                }
            ]
        }
        api_url = bob["gateway_url"] + "ob/ordercompletion"
        r = requests.post(api_url, data=json.dumps(oc, indent=4))
        if r.status_code == 404:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Completion post endpoint not found")
        elif r.status_code != 200:
            resp = json.loads(r.text)
            raise TestFailure("EthCompleteDisputedTest - FAIL: Completion POST failed. Reason: %s", resp["reason"])
        time.sleep(4)

        # check alice received completion
        api_url = alice["gateway_url"] + "ob/order/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Couldn't load order from Alice")
        resp = json.loads(r.text)
        if resp["state"] != "COMPLETED":
            raise TestFailure("EthCompleteDisputedTest - FAIL: Alice failed to detect order completion")

        # check bob set completion correctly
        api_url = bob["gateway_url"] + "ob/order/" + orderId
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("EthCompleteDisputedTest - FAIL: Couldn't load order from Bob")
        resp = json.loads(r.text)
        if resp["state"] != "COMPLETED":
            raise TestFailure("EthCompleteDisputedTest - FAIL: Bob failed to order completion")

        print("EthCompleteDisputedTest - PASS")


if __name__ == '__main__':
    print("Running EthCompleteDisputedTest")
    EthCompleteDisputedTest().main(["--regtest", "--disableexchangerates"])
