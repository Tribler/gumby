pragma solidity >0.4.13;

contract TaxiMatching {
	event Match(uint orderId1, uint orderId2, uint x1, uint y1, uint x2, uint y2, uint distance);

	struct Location {
		uint orderId;
		uint x;
		uint y;
	}

	Location[] requests;
	Location[] offers;

	function distance(Location memory l1, Location memory l2) private returns (uint) {
		uint x_diff = 0;
		if(l1.x > l2.x) { x_diff = l1.x - l2.x; }
		else { x_diff = l2.x - l1.x; }
		uint y_diff = 0;
		if(l1.y > l2.y) { y_diff = l1.y - l2.y; }
		else { y_diff = l2.y - l1.y; }

		return x_diff + y_diff;
	}

	function requestRide(uint orderId, uint x, uint y) public {
		Location memory l = Location(orderId, x, y);
		if(offers.length == 0) {
			requests.push(l);
			return;
		}

		// first check if there is any offer already
		bool foundOne = false;
		uint minDist = 0;
		uint offerIndex = 0;
		Location memory matchedOffer;
		for (uint i = 0; i < offers.length; i++) {
			uint dist = distance(l, offers[i]);
			if(!foundOne || dist < minDist) {
				minDist = dist;
				offerIndex = i;
				matchedOffer = offers[i];
				foundOne = true;
			}
		}

		emit Match(orderId, matchedOffer.orderId, x, y, matchedOffer.x, matchedOffer.y, minDist);

		if(offers.length > 1) {
			offers[offerIndex] = offers[offers.length-1];
		}
		offers.length--;
	}

	function offerRide(uint orderId, uint x, uint y) public {
		Location memory l = Location(orderId, x, y);
		if(requests.length == 0) {
			offers.push(l);
			return;
		}

		// first check if there is any request already
		uint minDist = 256 ** 2;
		uint requestIndex = 0;
		Location memory matchedRequest;
		for (uint i = 0; i < requests.length; i++) {
			uint dist = distance(l, requests[i]);
			if(dist < minDist) {
				minDist = dist;
				requestIndex = i;
				matchedRequest = requests[i];
			}
		}

		emit Match(orderId, matchedRequest.orderId, x, y, matchedRequest.x, matchedRequest.y, minDist);

		if(requests.length > 1) {
			requests[requestIndex] = requests[requests.length-1];
		}
		requests.length--;
	}

	function getNumOffers() public returns (uint) {
		return offers.length;
	}

	function getNumRequests() public returns (uint) {
		return requests.length;
	}
}

