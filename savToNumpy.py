# Import Python libraries
import sys
import clr
import numpy as np
from matplotlib import pyplot as plt
from pathlib import Path

# Add GAC references
sys.path.append("C:\\Windows\\Microsoft.NET\\assembly\\GAC_MSIL\\OpenTDv241\\v4.0_24.1.0.0__65e6d95ed5c2e178")
sys.path.append("C:\\Windows\\Microsoft.NET\\assembly\\GAC_64\\OpenTDv241.Results\\v4.0_24.1.0.0__b62f614be6a1e14a")
clr.AddReference("OpenTDv241")
clr.AddReference("OpenTDv241.Results")

# Include .NET Framework libraries
from System import *
from System.Collections.Generic import List
from OpenTDv241 import *
from OpenTDv241.Results.Dataset import *

def savToNumpy(
        saveFile: SaveFile,
        submodel: str,
        dataSubtypeNames: list[str],
    ):
    # Determine if current submodel is thermal or fluid
    thermalSubmodels = list(saveFile.GetThermalSubmodels())
    fluidSubmodels = list(saveFile.GetFluidSubmodels())

    if submodel in thermalSubmodels:
        dataType = DataTypes.NODE
    elif submodel in fluidSubmodels:
        dataType = DataTypes.LUMP
    else:
        raise IndexError(
            f"Submodel {submodel} is neither a thermal nor fluid submodel.\n" +
            f"Valid submodel names are:\n" +
            f"Thermal submodels: {thermalSubmodels}\n" +
            f"Fluid submodels: {fluidSubmodels}\n" 
        )

    itemIDs = ItemIdentifierCollection(dataType, submodel, saveFile)

    # Extract data
    data = {"units": {}}
    for dataSubtypeName in dataSubtypeNames:
        # Raw data
        dataSubtype = DataSubtype(FullStandardDataSubtype(dataSubtypeName))
        dataWrapper = saveFile.GetData(itemIDs, dataSubtype)
        dataValues = dataWrapper.GetValues()
        dataIDs = [
            dataID.ToString() for dataID in
            dataWrapper.SourceDataItemIdentifiers
        ]

        # Each row is a node/lump, each column is a timestep
        data[dataSubtypeName] = np.array(dataValues)
        data[dataSubtypeName+"-names"] = np.array(dataIDs)

        # Units
        dataDim = dataWrapper.Dimension
        data["units"][dataSubtypeName] = Units.WorkingUnits.GetUnitsName(dataDim)
    
    # Extract time
    # TODO: Better to make this into a class with named fields. Dictionary as
    # quick-and-dirty solution for now.
    data["time"] = np.array(saveFile.GetTimes().GetValues())
    
    return data


canonSavPath = Path() / "dummy_results" / "melt_frost_canon.sav"
testSavPath = Path() / "dummy_results" / "melt_frost_test.sav"
compareTypes = ["TL", "PL", "XL", "AL"]
submodel = "FLOW"
tolerance = 0.01

# Load datasets
Units.WorkingUnits.SetToSI()
canonSav = SaveFile(str(canonSavPath))
testSav = SaveFile(str(testSavPath))

# Extract values
canonData = savToNumpy(canonSav, submodel, compareTypes)
testData = savToNumpy(testSav, submodel, compareTypes)

# Plot example
# t = canonData["time"]
# for i, tdType in enumerate(compareTypes):
#     canonMean = np.mean(canonData[tdType], 0)
#     testMean = np.mean(testData[tdType], 0)
#     units = canonData["units"][tdType]

#     plt.figure(i + 1)
#     plt.plot(t, canonMean)
#     plt.plot(t, testMean, ':')
#     plt.legend(["Canonical", "Test"])
#     plt.title(f"Mean {tdType} of {submodel} submodel")
#     plt.xlabel("Time [s]")
#     plt.ylabel(f"{tdType} [{units}]")
# plt.show()

# Get exceedances
absDiff = {}
for tdType in compareTypes:
    absDiff[tdType] = np.abs(1 - testData[tdType]/canonData[tdType])
    exceedanceIdx = absDiff[tdType] > tolerance
    maxDiffIdx = np.unravel_index(
        absDiff[tdType].argmax(), absDiff[tdType].shape
    )

    print(
        f"Maximum difference at {testData[tdType+'-names'][maxDiffIdx[0]]}, " + 
        f"time = {testData['time'][maxDiffIdx[1]]}: " + 
        f"{absDiff[tdType][maxDiffIdx]*100:.2g}%"
    )