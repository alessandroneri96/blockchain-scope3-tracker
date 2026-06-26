// SPDX-License-Identifier: SEE LICENSE IN LICENSE
pragma solidity ^0.8.0;

/**
 * @title BatchTracker
 * @notice Records the CO2 emissions of every transport leg in a supply chain,
 *         enabling tamper-proof Scope 3 upstream carbon accounting.
 *
 * @dev Implements the distance-based method of the GHG Protocol (Category 4 —
 *      Upstream Transportation and Distribution) using average emission intensity
 *      factors per transport mode.
 *
 *      Based on:
 *        Neri, A., Butturi, M. A., Bonini, F., Lolli, F., & Gamberini, R. (2024).
 *        Blockchain-based carbon emissions tracking in supply chains: A smart
 *        contract solution for scope 3 reporting.
 *        Summer School Francesco Turco — Proceedings, 1–6.
 */
contract BatchTracker {

    struct Transfer {
        string newBatchId;
        string prevBatchId;
        uint256 batchSize;      // kg
        uint256 distance;       // km
        TransportMode transportMode;
        uint256 co2Emissions;   // g CO2e
    }

    enum TransportMode {
        TRUCK,
        AIRPLANE,
        SHIP
    }

    // Average CO2 emission rates (g CO2e / km) and vehicle capacities (kg).
    // Source: GHG Protocol — Category 4 guidance (indicative average values).
    uint256 constant TRUCK_EMISSION_RATE    = 123;
    uint256 constant AIRPLANE_EMISSION_RATE = 1012;
    uint256 constant SHIP_EMISSION_RATE     = 10;
    uint256 constant TRUCK_CAPACITY         = 3500;
    uint256 constant AIRPLANE_CAPACITY      = 23000;
    uint256 constant SHIP_CAPACITY          = 123450;

    // batchId → cumulative transfer history along the chain
    mapping(string => Transfer[]) public batchHistory;
    // newBatchId → prevBatchId (chain linkage)
    mapping(string => string) private batchIdLinks;

    event NewTransfer(
        string newBatchId,
        string prevBatchId,
        uint256 batchSize,
        uint256 distance,
        TransportMode transportMode,
        uint256 co2Emissions
    );

    /**
     * @notice Record a new transfer leg on-chain.
     *         The full history of prevBatchId is copied into newBatchId so that
     *         any downstream ID gives the complete upstream chain in one call.
     *
     * @param newBatchId     Identifier assigned to the batch after this leg.
     * @param prevBatchId    Identifier before this leg (empty string for origin).
     * @param batchSize      Batch weight in kg.
     * @param distance       Distance in km (use Haversine for geographic coords).
     * @param transportMode  0 = TRUCK | 1 = AIRPLANE | 2 = SHIP
     */
    function addTransfer(
        string memory newBatchId,
        string memory prevBatchId,
        uint256 batchSize,
        uint256 distance,
        TransportMode transportMode
    ) public {
        uint256 co2Emissions = calculateCO2Emissions(batchSize, distance, transportMode);

        Transfer memory newTransfer = Transfer(
            newBatchId,
            prevBatchId,
            batchSize,
            distance,
            transportMode,
            co2Emissions
        );

        if (batchHistory[prevBatchId].length == 0) {
            batchHistory[newBatchId].push(newTransfer);
        } else {
            Transfer[] storage prev = batchHistory[prevBatchId];
            for (uint i = 0; i < prev.length; i++) {
                batchHistory[newBatchId].push(prev[i]);
            }
            batchHistory[newBatchId].push(newTransfer);
        }

        batchIdLinks[newBatchId] = prevBatchId;

        emit NewTransfer(newBatchId, prevBatchId, batchSize, distance, transportMode, co2Emissions);
    }

    /**
     * @notice Returns the complete transfer history for a batch ID.
     *         The sum of co2Emissions across all entries is the Scope 3 footprint
     *         attributable to upstream transportation (GHG Protocol Category 4).
     */
    function getBatchHistory(
        string memory batchId
    ) public view returns (Transfer[] memory) {
        return batchHistory[batchId];
    }

    // CO2 [g] = (distance [km] × emission_rate [g/km] × batchSize [kg]) / capacity [kg]
    function calculateCO2Emissions(
        uint256 batchSize,
        uint256 distance,
        TransportMode transportMode
    ) internal pure returns (uint256) {
        if (transportMode == TransportMode.TRUCK) {
            return (distance * TRUCK_EMISSION_RATE * batchSize) / TRUCK_CAPACITY;
        } else if (transportMode == TransportMode.AIRPLANE) {
            return (distance * AIRPLANE_EMISSION_RATE * batchSize) / AIRPLANE_CAPACITY;
        } else if (transportMode == TransportMode.SHIP) {
            return (distance * SHIP_EMISSION_RATE * batchSize) / SHIP_CAPACITY;
        } else {
            revert("Invalid transport mode");
        }
    }
}
