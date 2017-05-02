# -*- coding: utf-8 -*-
#@author: ilyass.tabiai@polymtl.ca
#@author: rolland.delorme@polymtl.ca
#@author: patrick.diehl@polymtl.ca
import numpy as np
from scipy import linalg
from multiprocessing import Process, Lock
import sharedmem
from ..util import linalgebra
import sys

## Class to compute the global internal volumic force at each node of an elastic material using its material properties
class Viscoelastic_material():

    ## Constructor
    # @param deck The input deck
    # @param data_solver Data from the peridynamic problem/solving class
    # @param y Actual nodes' position
    # @param t_n Id of the time step
    def __init__(self, deck, data_solver, y, t_n):

        ## Influence function
        self.w = deck.influence_function

        ## Weighted volume
        self.Weighted_Volume = data_solver.weighted_volume

        if deck.dim == 1:
            ## Relaxation modulus of the material
            self.Relax_Modulus = deck.relax_modulus
            ## Relaxation time of the material
            self.Relax_Time = deck.relax_time

        if deck.dim == 2:
            print "Error: 2D problem not implemented in viscoelasticity"
            sys.exit(1)

        if deck.dim == 3:
            print "Error: 3D problem not implemented in viscoelasticity"
            sys.exit(1)

        ## Compute the dilatation for each node
        self.compute_dilatation(deck, data_solver, y)

        ## Compute the viscoelastic part of the dilatation for each node
        self.compute_dilatation_visco(deck, data_solver, y, t_n)

        ## Compute the global internal force density at each node
        self.compute_f_int(deck, data_solver, y)

    ## Compute the dilatation for each node
    # @param deck The input deck
    # @param data_solver Data from the peridynamic problem/solving class
    # @param y The actual nodes' position
    # @param start Starting Id of the loop
    # @param end Ending Id of the loop
    def compute_dilatation_slice(self, deck, data_solver, y, start, end):
        for i in range(start, end):
            index_x_family = data_solver.neighbors.get_index_x_family(i)
            for p in index_x_family:
                    Y = (y[p,:]) - y[i,:]
                    X = deck.geometry.nodes[p,:] - deck.geometry.nodes[i,:]
                    self.e[i,p] = linalgebra.norm(Y) - linalgebra.norm(X)

                    if deck.dim == 1:
                        self.dilatation[i] += (1. / self.Weighted_Volume[i]) * self.w * linalgebra.norm(X) * self.e[i,p] * deck.geometry.volumes[p]

                    if deck.dim == 2:
                        self.dilatation[i] += (2. / self.Weighted_Volume[i]) * self.factor2d * self.w * linalgebra.norm(X) * self.e[i,p] * deck.geometry.volumes[p]

                    if deck.dim == 3:
                        self.dilatation[i] += (3. / self.Weighted_Volume[i]) * self.w * linalgebra.norm(X) * self.e[i,p] * deck.geometry.volumes[p]

    ## Compute the dilatation and also the scalar extension state for each node
    # @param deck The input deck
    # @param data_solver Data from the peridynamic problem/solving class
    # @param y The actual nodes' position
    def compute_dilatation(self, deck, data_solver, y):
        ## Dilatation at each node
        self.dilatation = sharedmem.empty((deck.num_nodes),dtype=np.float64)
        ## Extension between Node "i" and Node "p" within its family
        self.e = sharedmem.empty((deck.num_nodes, deck.num_nodes),dtype=np.float64)

        threads = deck.num_threads
        part = int(deck.num_nodes/threads)

        processes = []

        for i in range(0,threads):
            start = i * part
            if i < threads - 1:
                end = (i+1) * part
            else:
                end = deck.num_nodes

            processes.append(Process(target=self.compute_dilatation_slice, args=(deck, data_solver, y, start, end)))
            processes[i].start()

        for p in processes:
            p.join()

    ## Compute the viscoelastic part of the scalar extension state
    # @param deck The input deck
    # @param data_solver Data from the peridynamic problem/solving class
    # @param y The actual nodes' position
    # @param t_n Id of the time step
    # @param start Starting Id of the loop
    # @param end Ending Id of the loop
    def compute_dilatation_visco_slice(self, deck, data_solver, y, t_n, start, end):
        for i in range(start, end):
            index_x_family = data_solver.neighbors.get_index_x_family(i)
            for p in index_x_family:
                X = deck.geometry.nodes[p,:] - deck.geometry.nodes[i,:]
                for k in range(1, len(self.Relax_Time)):
                    tmp_exp = np.exp((- deck.delta_t) / (self.Relax_Time[k]))
                    delta_e = self.e[i, p] - data_solver.ext[i, p, t_n-1]
                    beta = 1.0 - (self.Relax_Time[k] * (1.0 - tmp_exp)) / deck.delta_t
                    self.e_visco[i,p,k] = data_solver.ext[i, p, t_n-1] * (1.0 - tmp_exp) + data_solver.ext_visco[i, p, k, t_n-1] * tmp_exp + beta * delta_e

                    if deck.dim == 1:
                        self.dilatation_visco[i,k] += (1. / self.Weighted_Volume[i]) * self.w * linalgebra.norm(X) * (self.e[i,p] - self.e_visco[i, p, k]) * deck.geometry.volumes[p]

                    if deck.dim == 2:
                        self.dilatation_visco[i,k] += (2. / self.Weighted_Volume[i]) * self.factor2d * self.w * linalgebra.norm(X) * (self.e[i,p] - self.e_visco[i, p, k]) * deck.geometry.volumes[p]

                    if deck.dim == 3:
                        self.dilatation_visco[i,k] += (3. / self.Weighted_Volume[i]) * self.w * linalgebra.norm(X) * (self.e[i,p] - self.e_visco[i, p, k]) * deck.geometry.volumes[p]

    ## Compute the viscoelastic part of the scalar extension state
    # @param deck The input deck
    # @param data_solver Data from the peridynamic problem/solving class
    # @param y The actual nodes' position
    # @param t_n Id of the time step
    def compute_dilatation_visco(self, deck, data_solver, y, t_n):
        ## Dilatation at each node
        self.dilatation_visco = sharedmem.empty((deck.num_nodes, len(self.Relax_Time)),dtype=np.float64)
        ## Extension between Node "i" and Node "p" within its family
        self.e_visco = sharedmem.empty((deck.num_nodes, deck.num_nodes, len(self.Relax_Time)),dtype=np.float64)

        threads = deck.num_threads
        part = int(deck.num_nodes/threads)

        processes = []

        for i in range(0,threads):
            start = i * part
            if i < threads - 1:
                end = (i+1) * part
            else:
                end = deck.num_nodes

            processes.append(Process(target=self.compute_dilatation_visco_slice, args=(deck, data_solver, y, t_n, start, end)))
            processes[i].start()

        for p in processes:
            p.join()

    ## Compute the global internal force density at each node
    # @param deck The input deck
    # @param data_solver Data from the peridynamic problem/solving class
    # @param y The actual nodes' position
    # @param start Starting Id of the loop
    # @param end Ending Id of the loop
    def compute_f_int_slice(self, deck, data_solver, y, start, end, data):
        #print start , end
        for i in range(start, end):
            index_x_family = data_solver.neighbors.get_index_x_family(i)
            for p in index_x_family:
                Y = y[p,:] - y[i,:]
                X = deck.geometry.nodes[p,:] - deck.geometry.nodes[i,:]

                # Compute the direction vector between Node_p and Node_i
                M = Y / linalgebra.norm(Y)

                if deck.dim == 1:
                    t_visco = 0.0
                    for k in range(1, len(self.Relax_Time)):
                        # PD viscoelastic material parameter
                        alpha_k = self.Relax_Modulus[k] / self.Weighted_Volume[i]
                        # Viscoelastic par of the scalar force state
                        t_visco += alpha_k * self.w * (self.e[i,p] - self.e_visco[i,p,k])

                    # PD elast. material parameter
                    alpha_0 = self.Relax_Modulus[0] / self.Weighted_Volume[i]
                    ## Scalar force state
                    self.t = alpha_0 * self.w * self.e[i,p] + t_visco

                if deck.dim == 2:
                    # PD material parameter
                    # Plane stress
                    alpha_s = (9. / self.Weighted_Volume[i]) * (self.K + ((self.Nu + 1.)/(2. * self.Nu - 1.))**2 * self.Mu / 9.)
                    # Plane strain
                    #alpha_s = (9. / self.Weighted_Volume[i]) * (self.K + self.Mu / 9.)

                    alpha_d = (8. / self.Weighted_Volume[i]) * self.Mu
                    # Scalar force state
                    e_s = self.dilatation[i] * linalgebra.norm(X) / 3.
                    e_d = self.e[i, p] - e_s

                    t_s = (2. * self.factor2d * alpha_s - (3. - 2. * self.factor2d) * alpha_d) * self.w * e_s / 3.
                    t_d = alpha_d * self.w * e_d
                    self.t = t_s + t_d

                if deck.dim == 3:
                    # PD material parameter
                    alpha_s = (9. / self.Weighted_Volume[i]) * self.K
                    alpha_d = (15. / self.Weighted_Volume[i]) * self.Mu
                    # Scalar force state
                    e_s = self.dilatation[i] * linalgebra.norm(X) / 3.
                    e_d = self.e[i, p] - e_s
                    t_s = alpha_s * self.w * e_s
                    t_d = alpha_d * self.w * e_d
                    self.t = t_s + t_d

                #lock.acquire()
                data[i,:] += self.t * M * deck.geometry.volumes[p]
                data[p,:] += -self.t * M * deck.geometry.volumes[i]
                #lock.release()

    ## Compute the global internal force density at each node
    # @param deck The input deck
    # @param data_solver Data from the peridynamic problem/solving class
    # @param y The actual nodes' position
    def compute_f_int(self, deck, data_solver, y):
        ## Internal force density at each node
        self.f_int = sharedmem.empty((deck.num_nodes, deck.dim),dtype=np.float64)
        #self.f_int.fill(0.0)
        #lock = Lock()
        threads = deck.num_threads
        part = int(deck.num_nodes/threads)

        processes = []
        data = []
        for i in range(0,threads):
            start = i * part
            if i < threads - 1:
                end = (i+1) * part
            else:
                end = deck.num_nodes
            #print start , end , deck.num_nodes
            data.append(sharedmem.empty((deck.num_nodes, deck.dim),dtype=np.float64))
            #data[i].fill(0)
            processes.append(Process(target=self.compute_f_int_slice, args=(deck, data_solver, y, start, end, data[i])))
            processes[i].start()

        for p in processes:
            p.join()

        for i in range(0,threads):
            self.f_int += data[i]