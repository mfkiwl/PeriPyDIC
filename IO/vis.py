# -*- coding: utf-8 -*-
#@author: ilyass.tabiai@polymtl.ca
#@author: rolland.delorme@polymtl.ca
#@author: patrick.diehl@polymtl.ca

import pkgutil
vtk_loader = pkgutil.find_loader('vtk')
found_vtk = vtk_loader is not None 
if found_vtk == True:
    import vtk

class vtk_writer():
    

    if found_vtk == True:    

        def __init__(self,path,types,slice_length):
            ## IS vtk enabled
            self.vtk_enabled = True
            ## Path for the output
            self.path = path
            ## Types of the attributes
            self.types = types
            ## Slice for the timesteps
            self.slice_length = slice_length
            
        def write_data(self,deck,problem):
            num_nodes = deck.num_nodes
            for t in range(1,deck.time_steps,self.slice_length):
                writer = vtk.vtkXMLUnstructuredGridWriter()
                writer.SetFileName(self.path+"output_"+str(t)+".vtu")
                grid = vtk.vtkUnstructuredGrid()
                points = vtk.vtkPoints()
                points.SetNumberOfPoints(num_nodes)
                points.SetDataTypeToDouble()
                for i in range(0,num_nodes):
                    act = problem.y[:, t]
                    if deck.dim == 1:
                        points.InsertPoint(i,act[i],0.,0.)
                    if deck.dim == 2:
                        act = problem.y[:, t]
                        points.InsertPoint(i,act[i],act[num_nodes+i],0.)
                    if deck.dim == 3:
                        points.InsertPoint(i,problem.y[t][i],problem.y[t][num_nodes+i],problem.y[t][2*num_nodes+i])
                    grid.SetPoints(points)
                    dataOut = grid.GetPointData()    
                    for out_type in self.types:
                        
                        if out_type == "Displacement":
                            array = vtk.vtkDoubleArray()
                            array.SetName("Displacement")
                            array.SetNumberOfComponents(deck.dim)
                            array.SetNumberOfTuples(num_nodes)
                            
                            #if deck.dim >= 2:
                            act = problem.y[:, t]
                                  
                            for i in range(num_nodes):
                                if deck.dim == 1:
                                    array.SetTuple1(i,abs(act[i] - deck.geometry.nodes[i][0]))
                                if deck.dim == 2:
                                    array.SetTuple2(i,abs(act[i] - deck.geometry.nodes[i][0]),abs(act[num_nodes+i] - deck.geometry.nodes[i][1]))
                            dataOut.AddArray(array)
                        
                        if out_type == "Neighbors":
                            array = vtk.vtkIntArray()
                            array.SetName("Neighbors")
                            array.SetNumberOfComponents(1)
                            array.SetNumberOfTuples(num_nodes)
                            
                            for i in range(num_nodes):
                                 array.SetTuple1(i,len(problem.neighbors.get_index_x_family(i)))
                            dataOut.AddArray(array)
            
                        if out_type == "Force":
                            array = vtk.vtkDoubleArray()
                            array.SetName("Volume_Force")
                            array.SetNumberOfComponents(deck.dim)
                            array.SetNumberOfTuples(num_nodes)
                            
                            #if deck.dim >= 2:
                            act = problem.b[:, t]
                                  
                            for i in range(num_nodes):
                                if deck.dim == 1:
                                    array.SetTuple1(i,act[i])
                                if deck.dim == 2:
                                    array.SetTuple2(i,act[i], act[num_nodes+i])
                            dataOut.AddArray(array)
                            
                        if out_type == "Conditions":
                            
                            for con in deck.conditions:
                                array = vtk.vtkIntArray()
                                array.SetName("Condition_"+con.type+"_"+str(con.value)+"_"+str(con.direction))
                                array.SetNumberOfComponents(1)
                                array.SetNumberOfTuples(num_nodes)
                                
                                for i in range(num_nodes):
                                    if i not in con.id:
                                        array.SetTuple1(i,0)
                                    else:
                                         array.SetTuple1(i,1)
                                dataOut.AddArray(array)
            
                writer.SetInputData(grid)
            
                writer.GetCompressor().SetCompressionLevel(0)
                writer.SetDataModeToAscii()
                writer.Write()
        
    else:
    
        def __init__(self,path,types,slice_length):
            self.vtk_enabled = False