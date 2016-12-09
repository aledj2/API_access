'''
The API cannot be used on the trust network and MOKA cannot be accessed from outside the trust network so two scripts are required.
This script takes the output of the read_api script.
For each panel it checks if it is already in MOKA, and if the panel has been updated.
If it's a new panel the gene panel and genes are instered into MOKA.
This script was designed to be run repeatedly over time.

steps in more detail:
1) Look to see if 'NGS Panel Version' is in the lookup table. if not insert it.
2) Loop through the API result creating a list of version numbers 
3) Pull out all versions in the lookup table. Insert any version numbers that are not already in the database
4) Pull out the existing panels and versions from database. This creates a dictonary with panel_name as key and the values as a list of versions eg {epilepsy_green:[0.1,0.2]}
5) Loop through the API result:
    - check if the panel name is already in dict
        - checks if the version number from API is > than that in the db
            - If newer insert new panel name and version, deactivating the older version
6) Add the genes to the NGSpanelsGenes table

created by Aled 18 Oct 2016
'''
import pyodbc

class insert_PanelApp:
    def __init__(self):
        # the file containing the result of the API query
        self.API_result = "S:\\Genetics_Data2\\Array\\Audits and Projects\\161014 PanelApp\\PanelAppOut.txt"
        self.API_symbol_result = "S:\\Genetics_Data2\\Array\\Audits and Projects\\161014 PanelApp\\PanelAppOut_symbols.txt"
        
        # variables for the database connection
        self.cnxn = pyodbc.connect("DRIVER={SQL Server}; SERVER=GSTTV-MOKA; DATABASE=devdatabase;")
        self.cursor = self.cnxn.cursor()

        # name of category in item category
        self.category_name = "NGS Panel version"

        # list of versions for item table
        self.list_of_versions = [0.0]

        # query used when returning a key after select statement
        self.fetch_key_qry = ""
        self.exception_message = ""

        # query used for select_query
        self.select_qry = ""
        self.select_qry_exception = ""

        # used in insert query
        self.insert_query = ""
        self.insert_query_exception = ""

        # value for item_category_NGS_panel in item table
        self.item_category_NGS_panel = "48"

        # variable for the panel name and version
        self.panel_name_colour = ''
        self.panel_hash_colour=''

        # variable to hold all the panels currently in the database
        self.all_panels = {}

        # key assigned to panel in item table
        self.VersionItemCategory = ''

        # all versions in database
        self.versions_in_db = []

        # new version key
        self.version_key = ""

        # list of genes within panel
        self.ensembl_ids = ""

        # key of newly inserted panel
        self.inserted_panel_key = ""

        # variable to hold the key for the existing gene panel
        self.panel_key = ""
        
        #ignore exception flag
        self.ignore=False
        self.notfound="not found"
        
        self.moka_user="1201865448"

    def check_item_category_table(self):
        '''this module checks the itemcategory table to find the key that marks an row as a NGS panel version.
        If not present inserts it. This should only be required the first time'''
        # query to extract all rows in table
        self.select_qry = "select itemcategory from itemcategory"
        self.select_qry_exception = "cannot retrieve all itemcategories from itemcategory table"
        item_cat = self.select_query()
        # loop through the table contents and append to a list
        item_cat_list = []
        for i in item_cat:
            item_cat_list.append(i[0])
        # If there is no entry for NGS Panel version insert it 
        if self.category_name not in item_cat_list:
            self.insert_query = "Insert into Itemcategory(itemcategory) values ('" + self.category_name + "')"
            self.insert_query_function()

    def get_list_of_versions(self):
        '''The API results are parsed to identify all the version numbers'''
        # need to parse the API result to find all the version numbers
        API_result = open(self.API_result, 'r')
        # split to capture the version number
        for i in API_result:
            split1 = i.split(':')
            names = split1[0].split('_')
            version = float(names[2])

            # create a list of unique version numbers
            if version not in self.list_of_versions:
                self.list_of_versions.append(version)

        # Call module to insert any new version numbers to the database
        self.insert_versions()

    def insert_versions(self):
        '''If a version number from the API result is not in the database insert it'''
        
        # first need to get the key used to mark version numbers in the item table
        self.fetch_key_qry = "select ItemCategoryID from ItemCategory where ItemCategory = '" + self.category_name + "'"
        self.exception_message = "Cannot return the itemcategoryID from itemcategory table when looking for 'ngs panel version'"

        # call fetch key module
        version_item_cat = self.fetch_key()
        self.VersionItemCategory = version_item_cat[0]

        # get list of versions already in table
        self.select_qry = "select Item from item where itemcategoryindex1ID=" + str(self.VersionItemCategory)
        self.select_qry_exception = "cannot find any versions in item table"
        list_of_versions = self.select_query()
        
        #loop through results and append to a list
        for i in list_of_versions:
            self.versions_in_db.append(float(i[0]))
        
        # if version in API result not already in db:
        for version in self.list_of_versions:
            if version not in self.versions_in_db:
                # add the version to the item table
                self.insert_query = "Insert into Item(Item,itemcategoryindex1ID) values (" + str(version) + "," + str(self.VersionItemCategory) + ")"
                self.insert_query_function()

    def all_existing_panels(self):
        '''This module extracts all the panels and the version numbers from the database'''
        # extract all the existing panels from the database
        self.select_qry = "select ItemA.item, ItemB.item from Item itemA, Item ItemB, NGSPanel where ItemA.ItemID=dbo.NGSPanel.Category and ItemB.itemID = dbo.NGSPanel.subCategory and itemA.ItemCategoryIndex1ID = " + str(self.item_category_NGS_panel) + " and itemB.ItemCategoryIndex1ID=" + str(self.VersionItemCategory)
        self.select_qry_exception = "cannot extract all panels and versions"
        
        # set flag so exception is not raised - this exception will only occur upon the very first insert 
        self.ignore=True
        all_panels = self.select_query()
        # if no panels in gene all_panels will be empty- looping through this will error!
        if all_panels == self.notfound:
            pass
        else:
            # loop through db results result and create a dict with the panel name as key and list of version numbers as value
            for i in all_panels:
                #i[0] is panel name, i[1] is version number
                #if panel_name already in dict, just add the version number
                panelhash=str(i[0])
                version=float(i[1])
                if panelhash in self.all_panels:
                    self.all_panels[panelhash].append(version)
                else:
                    # otherwise add dictionary entry
                    self.all_panels[panelhash] = [version]
        # unset ignore flag
        self.ignore=False
        #print self.all_panels

    def parse_PanelAPP_API_result(self):
        ''' This module loops through the API result. If the panel name is not in the database it inserts it. 
        If the panel already exists it checks the version number to see if the panel has been updated and if so the updated verison is inserted'''
        # open and parse the text file containing the api query result
        API_result = open(self.API_result, 'r')
        #loop through and extract required info
        for i in API_result:
            # split - example line  = Epidermolysis bullosa_0.8_amber:[list,of,ensemblids]
            split1 = i.split(':')
            self.ensembl_ids = split1[1]
            names = split1[0].split('_')
            # removing any "'" from panel_name (messes up the sql query)
            panel_hash = str(names[0])
            panel_name = str(names[1].replace("'",""))
            version = float(names[2])
            colour = str(names[3])
            
            #define the panel name as disease name and panel colour
            self.panel_hash_colour=panel_hash+"_"+colour
            self.panel_name_colour=panel_name+"_"+colour
            
            # check if panel is already in the database
            if self.panel_hash_colour in self.all_panels:
                #print "panel present" + self.panel_name_colour 
                self.fetch_key_qry = "select itemid from item where item = '" + self.panel_hash_colour + "'"
                panel_id = self.fetch_key()
                self.panel_key = panel_id[0]

            # if not insert to items table
            else:
                print "panel not present "+self.panel_name_colour, self.panel_hash_colour
                self.insert_query_return_key = "insert into item(item,ItemCategoryIndex1ID) values ('" + self.panel_hash_colour+ "'," + self.item_category_NGS_panel + ")"
                key=self.insert_query_return_key_function()
                self.panel_key=key[0]

            #### Has the panel been updated?
            # get the maximum version number from the existing panels in db
            if self.panel_hash_colour in self.all_panels:
                max_version = max(self.all_panels[self.panel_hash_colour])
                exists=True
            else:
                max_version=-1
                exists=False
            # if this panel is newer get the key for this version number from item table (all versions were inserted above)
            if version > max_version:
                if exists:
                    # first, if it exists need to deactivate the existing panel
                    self.insert_query="update ngspanel set active = 0 where category = "+ str(self.panel_key)
                    self.insert_query_function()
                # then get the itemid of the version 
                self.select_qry = "select itemid from item where item in ('" + str(version) + "') and ItemCategoryIndex1ID = " + str(self.VersionItemCategory)
                self.select_qry_exception = "Cannot get key for version number"
                version_key = self.select_query()
                self.version_key = version_key[0][0]

                # Insert the NGSpanel, returning the key 
                self.insert_query_return_key = "insert into ngspanel(category, subcategory, panel, panelcode, active, checker1,checkdate,PanelType) values (" + str(self.panel_key) + "," + str(self.version_key) + ",'" + self.panel_name_colour+"_"+str(version) + "','Pan',1,"+self.moka_user+",CURRENT_TIMESTAMP,2)" 
                self.insert_query_exception="cannot get the key when inserting this panel"
                key=self.insert_query_return_key_function()
                self.inserted_panel_key= key[0]
                # update the table so the Pan number is created.
                self.insert_query = "update NGSPanel set PanelCode = PanelCode+cast(NGSPanelID as VARCHAR) where NGSPanelID = "+str(self.inserted_panel_key)
                self.insert_query_function()

                # Call module to insert gene list to NGSPanelGenes.
                self.add_genes_to_NGSPanelGenes()
                
            
            # if not a new version ignore
            else:
                pass
    
    def add_genes_to_NGSPanelGenes(self):
        '''This module inserts the list of genes into the NGSGenePanel. The HGNC table is queried to find the symbol and HGNCID from the ensembl id'''
        # list of cleaned gene ids:
        list_of_genes_cleaned=[]
        
        # convert the string containing gene list into a python list
        # split and remove all unwanted characters
        list_of_genes=self.ensembl_ids.split(",")
        for i in list_of_genes:
            i=i.replace("\"","").replace("[","").replace("]","").replace(" ","").rstrip()
            # append to list
            list_of_genes_cleaned.append(i)
        
        #print list_of_genes_cleaned
        #loop through gene list
        for ensbl_id in list_of_genes_cleaned:
            if len(ensbl_id)<5:
                pass
            else:
            # for each gene get the HGNCID and ApprovedSymbol
                #set ignore flag to ignore exception
                self.ignore=True
                self.select_qry="select HGNCID,PanelApp_Symbol from dbo.GenesHGNC_current_translation where EnsemblIDmapped="+str(ensbl_id.replace("u",""))
                self.select_qry_exception=self.panel_name_colour+" can't find the gene from ensembl_id: "+str(ensbl_id)
                #print self.select_qry
                #print ensbl_id
                gene_info=self.select_query()
                if gene_info==self.notfound:
                    #print self.select_qry_exception
                    pass
                else:
                    HGNCID=gene_info[0][0]
                    ApprovedSymbol=gene_info[0][1]
                    
                    # insert each gene into the NGSPanelGenes table
                    self.insert_query="insert into NGSPanelGenes(NGSPanelID,HGNCID,symbol,checker,checkdate) values ("+str(self.inserted_panel_key)+",'"+HGNCID+"','"+ApprovedSymbol+"',"+self.moka_user+",CURRENT_TIMESTAMP)"
                    #print self.insert_query
                    self.insert_query_exception="can't insert gene into the NGSPanelGenes table"
                    self.insert_query_function()

        self.ignore=False
        self.insert_missing_gene_symbols()
    
    def insert_missing_gene_symbols(self):
        # open and parse the text file containing the api query result
        API_symbols = open(self.API_symbol_result, 'r')
        #loop through and extract required info
        for i in API_symbols:
            #print i
            # split - example line  = Epidermolysis bullosa_0.8_amber:[list,of,ensemblids]
            split1 = i.split(':')
            self.ensembl_ids = split1[1]
            names = split1[0].split('_')
            
            # removing any "'" from panel_name (messes up the sql query)
            panel_name = names[1].replace("'","")
            version = names[2]
            colour = names[3]
            
            panel_name_colour=panel_name+"_"+colour
            #print panel_name_colour
            
            if self.panel_name_colour==panel_name_colour:
                #print "panel match"
                api_symbol_list=[]
                genes=split1[1].split(',')
                for gene in genes:
                    gene = gene.replace("[","").replace("'","").replace("[","").replace("'","").replace("]","").replace(" ","").replace("\n","").rstrip()
                    api_symbol_list.append(str(gene))
                
                #print api_symbol_list
                self.select_qry="select Symbol from dbo.NGSPanel, dbo.NGSPanelGenes where dbo.NGSPanel.NGSPanelID = dbo.NGSPanelgenes.NGSPanelID and Panel = '"+self.panel_name_colour+"_"+version+"'"
                self.select_qry_exception="Cannot find the genes in this panel:"+self.panel_name_colour
                panel_genes=self.select_query()
                db_list=[]
                #print panel_genes[0]
                for i in panel_genes:
                    db_list.append(str(i[0]))
                #print db_list
                self.select_qry="select PanelApp_Symbol from dbo.GenesHGNC_current_translation where PanelAppGeneSymbolCheck is not null"
                self.select_qry_exception="Cannot retrieve the list of manually curated genes which differ between HGNC and panelapp"
                curated_genes=self.select_query()
                incorrect_genesymbol_list=[]
                
                #print curated_genes
                for i in curated_genes:
                    #print i
                    incorrect_genesymbol_list.append(str(i[0]))
                #print incorrect_genesymbol_list
                
                for api_gene in api_symbol_list:
                    if api_gene not in db_list:
                        if api_gene not in incorrect_genesymbol_list:
                            print api_gene+" cannot be added to moka as it cannot be linked to HGNC_current_translation table via ensemblid and has not been manually curated. "+self.panel_name_colour
                        else:
                            self.select_qry="select HGNCID from dbo.GenesHGNC_current_translation where PanelApp_Symbol='"+api_gene+"'"
                            self.select_qry_exception="Cannot find the HGNCID for "+ api_gene
                            HGNCID_result=self.select_query()
                            HGNC=HGNCID_result[0][0]
                            self.insert_query="insert into NGSPanelGenes(NGSPanelID,HGNCID,symbol,checker,checkdate) values ("+str(self.inserted_panel_key)+",'"+HGNC+"','"+api_gene+"',"+self.moka_user+",CURRENT_TIMESTAMP)"
                            self.insert_query_exception="can't insert gene into the NGSPanelGenes table"
                            #print self.insert_query
                            self.insert_query_function()


    def check_all_gene_symbols_are_in_db(self):
        # open and parse the text file containing the api query result
        API_symbols = open(self.API_symbol_result, 'r')
        #loop through and extract required info
        for i in API_symbols:
            # split - example line  = Epidermolysis bullosa_0.8_amber:[list,of,ensemblids]
            split1 = i.split(':')
            self.ensembl_ids = split1[1]
            names = split1[0].split('_')
            # removing any "'" from panel_name (messes up the sql query)
            panel_name = names[1].replace("'","")
            version = names[2]
            colour = names[3]
            
            api_symbol_list=[]
            genes=split1[1].split(',')
            for gene in genes:
                gene = str(gene.replace("[","").replace("'","").replace("[","").replace("'","").replace("]","").replace(" ","").replace("\n","").rstrip())
                api_symbol_list.append(str(gene))
            

            # define the panel name as disease name and panel colour
            self.panel_name_colour=panel_name+"_"+colour
            
            self.select_qry="select PanelApp_Symbol from dbo.NGSPanel, dbo.NGSPanelGenes,dbo.GenesHGNC_current_translation where dbo.GenesHGNC_current_translation.HGNCID=dbo.NGSPanelGenes.HGNCID and dbo.NGSPanel.NGSPanelID = dbo.NGSPanelgenes.NGSPanelID and Panel = '"+self.panel_name_colour+"_"+str(version)+"'"
            self.select_qry_exception="Cannot find the genes in this panel:"+self.panel_name_colour
            
            panel_genes=self.select_query()
            db_list=[]
            
            for i in panel_genes:
                db_list.append(str(i[0]))
            
        
            count=0
            #print "missing:"
            #for gene in db_list:
                #if gene not in api_symbol_list:
                    #print gene+" not in api"
            for gene in api_symbol_list:
                if gene not in db_list:
                    if self.panel_name_colour.startswith("Mitochondrial disorders"):
                        pass
                    else:
                        if count == 0:
                            print self.panel_name_colour
                            count=count+1
                            print gene+" not in db"
                        else:
                            print gene+" not in db"
                            
                            
            for gene in db_list:
                if gene not in api_symbol_list:
                    if self.panel_name_colour.startswith("Mitochondrial disorders"):
                        pass
                    else:
                        if count == 0:
                            print self.panel_name_colour
                            count=count+1
                            print gene+" not in api"
                        else:
                            print gene+" not in api"
                #print "API:", str(len(api_symbol_list)),str(api_symbol_list)
                #print "db:" ,str(len(db_list)), str(db_list)

    def fetch_key(self):
        '''This function is called to retrieve a single entry from a select query'''
        # Perform query and fetch one
        result = self.cursor.execute(self.fetch_key_qry).fetchone()

        # return result
        if result:
            return(result)
        else:
            raise Exception(self.exception_message)

    def select_query(self):
        '''This function is called to retrieve the whole result of a select query '''
        # Perform query and fetch all
        result = self.cursor.execute(self.select_qry).fetchall()

        # return result
        if result:
            return(result)
        elif self.ignore:
            return(self.notfound)
        else:
            raise Exception(self.select_qry_exception)

    def insert_query_function(self):
        '''This function executes an insert query'''
        # execute the insert query
        self.cursor.execute(self.insert_query)
        self.cursor.commit()

    def insert_query_return_key_function(self):
        '''This function executes an insert query and returns the key of the newly created row'''
        # Perform insert query and return the key for the row
        self.cursor.execute(self.insert_query_return_key)
        self.cursor.commit()
        #capture key
        self.cursor.execute("SELECT @@IDENTITY")
        key = self.cursor.fetchone()
 
        # return result
        if key:
            return(key)
        elif self.ignore:
            return(self.notfound)
        else:
            raise Exception(self.insert_query_exception)


if __name__ == "__main__":
    a = insert_PanelApp()
    a.check_item_category_table()
    a.get_list_of_versions()
    a.all_existing_panels()
    a.parse_PanelAPP_API_result()
    a.check_all_gene_symbols_are_in_db()
