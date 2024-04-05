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

# Data subtype string to object map
dataSubtypeMap = {
    "T": StandardDataSubtypes.T,
    "TL": StandardDataSubtypes.TL,
    "PL": StandardDataSubtypes.PL,
    "AL": StandardDataSubtypes.AL,
    "XL": StandardDataSubtypes.XL,
}

def savToNumpy(
        saveFile: SaveFile,
        submodel: str,
        dataSubtypes: list[str],
        thermal: bool = True,
    ):
    if thermal:
        dataType = DataTypes.NODE
    else:
        dataType = DataTypes.LUMP

    itemIDs = ItemIdentifierCollection(dataType, submodel, saveFile)

    # Extract data
    data = {"units": {}}
    for dataSubtype in dataSubtypes:
        # Raw data
        dataWrapper = saveFile.GetData(
            itemIDs,
            DataSubtype(dataSubtypeMap[dataSubtype])
        )
        dataValues = dataWrapper.GetValues()
        data[dataSubtype] = np.array(dataValues)

        # Units
        dataDim = dataWrapper.Dimension
        data["units"][dataSubtype] = Units.WorkingUnits.GetUnitsName(dataDim)
    
    # Extract time
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
canonData = savToNumpy(canonSav, submodel, compareTypes, thermal=False)
testData = savToNumpy(testSav, submodel, compareTypes, thermal=False)

# Plot example
t = canonData["time"]
for i, tdType in enumerate(compareTypes):
    canonMean = np.mean(canonData[tdType], 0)
    testMean = np.mean(testData[tdType], 0)
    units = canonData["units"][tdType]

    plt.figure(i + 1)
    plt.plot(t, canonMean)
    plt.plot(t, testMean, ':')
    plt.legend(["Canonical", "Test"])
    plt.title(f"Mean {tdType} of {submodel} submodel")
    plt.xlabel("Time [s]")
    plt.ylabel(f"{tdType} [{units}]")
plt.show()