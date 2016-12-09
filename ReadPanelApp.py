'''
Created on 13/Oct/2016

This script reads the PanelAPP API and loops through all the gene panels.

For each panel a list of red, amber and green ensembl ids are collected in a dictionary.

@author: aled
'''

import requests


class PanelAPP_API():

    def __init__(self):
        # define the apis urls. both set to return json.
        self.list_of_panels = "https://bioinfo.extge.co.uk/crowdsourcing/WebServices/list_panels?format=json"
        # need to append the panel name on end
        self.list_of_genes = "https://bioinfo.extge.co.uk/crowdsourcing/WebServices/get_panel/"

        # set up the dictionary to collate all the panels
        self.dict_of_panels = {}
        
        # output_file
        self.outputfilepath="/home/aled/Documents/PanelApp/"

    def get_list_of_panels(self):
        ''' Retrieve all the gene panels from the PanelAPP url. Create an dictionary key for each one made up of a tuple of the panel name and version number'''

        # the response package retrieves the results of the url search
        response = requests.get(self.list_of_panels)

        # this is captured as a json object
        json_results = response.json()

        # loop through each panel within the json
        for panel in json_results["result"]:
            
            # create a tuple of the name and version
            toople = (str(panel["Panel_Id"]),str(panel["Name"]), float(panel["CurrentVersion"]))
            
            # create a dictionary key with this tuple and an empty dictionary as the value
            self.dict_of_panels[toople] = {}

        # call next module
        self.get_genes_in_panel()

    def get_genes_in_panel(self):
        '''This module loops through each panel and retrieves the genes within this panel as a json'''
        # loop through dict
        for i in self.dict_of_panels:
            # split the tuple
            panelID = i[0]

            # the response package retrieves the results of the url search
            response = requests.get(self.list_of_genes + panelID+"/?format=json")
            
            # this is captured as a json object
            json_results = response.json()

            # create some empty lists to hold the gene lists
            red_list = []
            amber_list = []
            green_list = []
            
            red_symbol_list = []
            amber_symbol_list = []
            green_symbol_list = []
            
            # loop through each gene in the json
            for gene in json_results["result"]["Genes"]:
                ensemblid_list=[]
                ensemblids=gene["EnsembleGeneIds"]
                for ensemblid in ensemblids:
                    ensemblid_list.append(str(ensemblid))                 
                                        
                symbol = str(gene["GeneSymbol"])

                # some genes have multiple ensembl gene ids. combine these into a sql friendly string
                ensemblid = "'" + '\',\''.join(ensemblid_list) + "'"  # plan is to use if gene in this string

                # each gene is red amber or green based on the evidence. Using this assign each gene into relevant gene list
                if gene["LevelOfConfidence"] == "HighEvidence":
                    green_list.append(ensemblid)
                    green_symbol_list.append(symbol)
                if gene["LevelOfConfidence"] == "ModerateEvidence":
                    amber_list.append(ensemblid)
                    amber_symbol_list.append(symbol)
                if gene["LevelOfConfidence"] == "LowEvidence":
                    red_list.append(ensemblid)
                    red_symbol_list.append(symbol)

            # populate the dictionary for this panel with an entry for each gene list
            #self.dict_of_panels[i]["Red"] = red_list
            self.dict_of_panels[i]["Amber"] = amber_list
            self.dict_of_panels[i]["Green"] = green_list
            
            # populate the dictionary for this panel with an entry for each gene list
            #self.dict_of_panels[i]["red_symbols"] = red_symbol_list
            self.dict_of_panels[i]["Amber_symbols"] = amber_symbol_list
            self.dict_of_panels[i]["Green_symbols"] = green_symbol_list
            
        # call module to write output file 
        self.write_output()
            
    def write_output(self):
        #open two files, one to capture all ensembl ids for each panel and one to capture a list of symbols.
        outputfile=open(self.outputfilepath+"PanelAppOut.txt",'w')
        symbols_outputfile=open(self.outputfilepath+"PanelAppOut_symbols.txt",'w')
        # for each panel
        for i in self.dict_of_panels:
            # for each colour
            for j in self.dict_of_panels[i]:
                # if it's a gene symbol panel  
                if "symbols" in j:
                    " if no symbols for this panel"
                    if len(self.dict_of_panels[i][j])==0:
                        pass
                    else:
                        # write line so looks like panelhash_panelname_version_colour_symbols:['list','of','gene','symbols']
                        # eg. 553f968cbb5a1616e5ed45cc_Classical tuberous sclerosis_1.0_Green_symbols:['TSC1', 'TSC2']
                        symbols_outputfile.write(str(i[0])+"_"+str(i[1])+"_"+str(i[2])+"_"+j+":"+str(self.dict_of_panels[i][j])+"\n")
                else:
                    #repeat for ensembl ids
                    if len(self.dict_of_panels[i][j])==0:
                        pass
                    else:
                        outputfile.write(str(i[0])+"_"+str(i[1])+"_"+str(i[2])+"_"+j+":"+str(self.dict_of_panels[i][j])+"\n")
        outputfile.close()
        symbols_outputfile.close()

if __name__ == "__main__":
    # create object
    a = PanelAPP_API()
    a.get_list_of_panels()
