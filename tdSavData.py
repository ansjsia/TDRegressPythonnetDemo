# Import Python libraries
import sys
import clr
import numpy as np
import pandas as pd
from pathlib import Path
from typing_extensions import Self

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

class TdSavData:
    def __init__(
            self,
            saveFilePath: str | Path,
            isCanonical: bool,
            submodel: str,
            dataSubtypeNames: list[str] = None,
        ):
        # TODO: Rewrite to support storing multiple submodels under the same
        # object
        
        self.saveFilePath = saveFilePath
        self.isCanonical = isCanonical

        if dataSubtypeNames is None:
            raise NotImplementedError("Automatically grabbing all data subtypes not supported yet.")
        
        # Read savefile
        saveFile = SaveFile(str(saveFilePath))

        # Determine if submdoel is thermal or fluid
        thermalSubmodels = list(saveFile.GetThermalSubmodels())
        fluidSubmodels = list(saveFile.GetFluidSubmodels())
        
        # TODO: Add support for other datatypes:
        #   REGISTER, CONDUCTOR, PATH, TIE, FTIE, IFACE
        if submodel in thermalSubmodels:
            dataType = DataTypes.NODE
        elif submodel in fluidSubmodels:
            dataType = DataTypes.LUMP
        else:
            raise Exception(
                f"Submodel {submodel} is neither a thermal nor fluid submodel.\n" +
                f"Valid submodel names are:\n" +
                f"Thermal submodels: {thermalSubmodels}\n" +
                f"Fluid submodels: {fluidSubmodels}\n" 
            )
        
        # Extract data
        self.data = {}
        for dataSubtypeName in dataSubtypeNames:
            dataObj = TdDataObject(
                saveFile,
                submodel,
                dataType,
                dataSubtypeName,
            )
            self.data[dataSubtypeName] = dataObj
    
    def compare(
            self,
            other: Self,
            tolerance: float = 0.01,
            compareSubtypes: list[str] = None,
        ) -> dict:
        # Set correct dataset to canonical
        if self.isCanonical and not other.isCanonical:
            canonData = self.data
            testData = other.data
        elif not self.isCanonical and other.isCanonical:
            canonData = other.data
            testData = self.data
        elif self.isCanonical and other.isCanonical:
            raise Exception(
                "Both datasets being compared are canonical. Only one of " +
                "the datasets being compared can be canonical."
            )
        else:
            raise Exception(
                "Neither dataset being compared is canonical. Exactly one " +
                "of the datasets being compared must be canonical."
            )
        
        # Get data subtypes in each dataset
        canonSubtypes = set(canonData.keys())
        testSubtypes = set(testData.keys())

        if canonSubtypes != testSubtypes:
            raise KeyError(
                f"Data subtypes of canonical dataset do not match those of " +
                f"the test dataset.\n" +
                f"Canonical dataset subtypes: {canonSubtypes}\n" +
                f"Test dataset subtypes: {testSubtypes}\n"
            )

        if compareSubtypes is None:
            compareSubtypes = canonSubtypes
        else:
            compareSubtypes = set(compareSubtypes)
            # Check that all types requested for compare are available
            if not ((compareSubtypes & canonSubtypes) == compareSubtypes):
                raise KeyError(
                    f"Data subtypes requested for comparison are not " +
                    f"available in the dataset.\n" +
                    f"Requested for comparison: {compareSubtypes}\n" +
                    f"Available in dataset: {canonSubtypes}\n"
                )
        
        exceedances = {}
        for dataSubtype in canonData.keys():
            canonSubdata = canonData[dataSubtype].dataValues
            testSubdata = testData[dataSubtype].dataValues
            
            # Check that submodels are the same
            canonSubmodel = canonData[dataSubtype].submodel
            testSubmodel = testData[dataSubtype].submodel
            if canonSubmodel != testSubmodel:
                raise Exception(
                    f"Submodels for comparison of {dataSubtype} are not " +
                    f"equal.\n" +
                    f"Canonical submodel: {canonSubmodel}\n" +
                    f"Test submodel: {testSubmodel}\n"
                )

            diff = (testSubdata - canonSubdata)/canonSubdata
            rows, cols = np.where(np.abs(diff) > tolerance)

            excIDs = testData[dataSubtype].dataIdentifiers[rows]
            excTimes = testData[dataSubtype].time[cols]

            # Output exceedances by subtype
            if excIDs.size > 0:
                exceedances[canonSubmodel] = {
                        dataSubtype: {
                        'IDs': excIDs,
                        'Times': excTimes,
                        'Errors': diff[rows, cols],
                    },
                }
        
        return exceedances
    
class TdDataObject:
    def __init__(
            self,
            saveFile: SaveFile,
            submodel: str,
            dataType: DataTypes,
            dataSubtypeName: str,
        ):
        self.submodel = submodel
        self.dataSubtype = dataSubtypeName

        # Extract save file data
        itemIDs = ItemIdentifierCollection(dataType, submodel, saveFile)
        dataSubtype = DataSubtype(FullStandardDataSubtype(dataSubtypeName))
        dataWrapper = saveFile.GetData(itemIDs, dataSubtype)

        self.dataValues = np.array(dataWrapper.GetValues())
        self.dataIdentifiers = np.array([
            dataID.ToString() for dataID in
            dataWrapper.SourceDataItemIdentifiers
        ])
        self.time = np.array(saveFile.GetTimes().GetValues())

        # Get units
        dataDim = dataWrapper.Dimension
        self.units = Units.WorkingUnits.GetUnitsName(dataDim)
    
    def getDataframe(self) -> pd.DataFrame:
        return pd.DataFrame(
            data=self.dataValues,
            index=self.dataIdentifiers,
            columns=self.time,
        )

if __name__ == "__main__":
    canonSavPath = Path() / "dummy_results" / "melt_frost_canon.sav"
    testSavPath = Path() / "dummy_results" / "melt_frost_test.sav"
    compareSubtypes = ["TL", "PL", "XL", "AL"]
    submodel = "FLOW"
    tolerance = 1e-6

    canon = TdSavData(canonSavPath, True, submodel, compareSubtypes)
    test = TdSavData(testSavPath, False, submodel, compareSubtypes)

    exceedances = canon.compare(test, tolerance=tolerance)

    print("End of program")