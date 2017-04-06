# -*- coding: utf-8 -*-
#@author: ilyass.tabiai@polymtl.ca
#@author: rolland.delorme@polymtl.ca
#@author: patrick.diehl@polymtl.ca
import numpy as np
from scipy import linalg
np.set_printoptions(precision=8, threshold='nan')
import sys

## Class to compute, as a vector state, the global internal volumic force of an elastic material using its material properties
class CCM_calcul():

    ## Constructor
    # @param deck The input deck
    # @param problem The related peridynamic problem
    # @param y The actual postions
    def __init__(self, deck, problem):
        ## Scalar influence function
        self.x = deck.geometry.nodes
        self.y = problem.y
        self.force_int = problem.force_int
        self.ext = problem.ext
        
        self.dim = deck.dim
        self.num_nodes = deck.num_nodes
        self.time_steps = deck.time_steps
        self.node_volumes = deck.geometry.volumes        
        self.influence_function = deck.influence_function
        
#        self.compute_C_stiffness_tensor(deck)     
        #self.compute_u_displacement()
        self.global_strain_tensor(problem)
#        self.global_stress_tensor(problem)

    # Compute the displacement for each node
    def compute_u_displacement(self):
        self.u = np.zeros((self.num_nodes, self.dim, self.time_steps),dtype=np.float64)
        for t_n in range(1, self.time_steps):
            for i in range(0, self.num_nodes):
                self.u[i,:,t_n] = self.y[i,:,t_n] - self.y[i,:,t_n-1]
                
#    # Compute the stiffness tensor
#    def compute_C_stiffness_tensor(self, deck):      
#        delta = np.identity(self.dim, dtype=np.float64)
#        
#        J = np.zeros((self.dim, self.dim, self.dim, self.dim),dtype=np.float64)
#        for i in range(0, self.dim):
#            for j in range(0, self.dim):
#                for k in range(0, self.dim):
#                    for l in range(0, self.dim):
#                        J[i,j,k,l] = (1./3.) * delta[i,j]*delta[k,l]
#
#        I = np.zeros((self.dim, self.dim, self.dim, self.dim),dtype=np.float64)
#        for i in range(0, self.dim):
#            for j in range(0, self.dim):
#                for k in range(0, self.dim):
#                    for l in range(0, self.dim):
#                        I[i,j,k,l] = (1./2.) * ( delta[i,k]*delta[j,l] + delta[i,l]*delta[j,k] )
#
#        K = np.zeros((self.dim, self.dim, self.dim, self.dim),dtype=np.float64)
#        for i in range(0, self.dim):
#            for j in range(0, self.dim):
#                for k in range(0, self.dim):
#                    for l in range(0, self.dim):
#                        K[i,j,k,l] = I[i,j,k,l] - J[i,j,k,l]
#        
#        if self.dim ==1:
#            bulk_modulus = deck.young_modulus / 3.
#            shear_modulus = deck.young_modulus /2.
#        
#        if self.dim >= 2:
#            bulk_modulus = deck.bulk_modulus
#            shear_modulus = deck.shear_modulus
#            
#        self.C = 3 * bulk_modulus * J + 2 * shear_modulus * K
            
    # Return the image of (xi - xp) under the reference position vector state X 
    def X_vector_state(self, problem, i, p):
        image = self.x[p,:] - self.x[i,:]
        image = np.reshape(image,(self.dim,1))
        return image

    # Return the image of (xi - xp) under the deformation vector state Y 
    def Y_vector_state(self, problem, i, p, t_n):
        image = self.y[p,:,t_n] - self.y[i,:,t_n]
        image = np.reshape(image,(self.dim,1))
        return image
        
    # Return the shape tensor K related to node i
    def K_shape_tensor(self, problem, i):
        K = np.zeros((self.dim, self.dim),dtype=np.float64)
        index_x_family = problem.neighbors.get_index_x_family(i)
        for p in index_x_family:
            X = self.X_vector_state(problem, i, p)
            K += self.influence_function * np.dot(X,X.T) * self.node_volumes[p]
        return K

    # Return the deformation gradient tensor epsilon related to node i
    def deformation_gradient(self, problem, i, t_n):
        tmp = np.zeros((self.dim, self.dim),dtype=np.float64)       
        index_x_family = problem.neighbors.get_index_x_family(i)
        for p in index_x_family:
            Y = self.Y_vector_state(problem, i, p, t_n)            
            X = self.X_vector_state(problem, i, p)
            tmp += self.influence_function * np.dot(Y,X.T) * self.node_volumes[p]
        deformation = np.dot(tmp, linalg.inv(self.K_shape_tensor(problem, i)))
        return deformation
        

    # Return the strain tensor related to node i
    def strain_tensor(self, problem, i, t_n):
        F = self.deformation_gradient(problem, i, t_n)
        strain = (F + F.T)/2 - np.identity(self.dim, dtype=np.float64)
        return strain

    # Return the strain tensor for each node
    def global_strain_tensor(self, problem):
        self.global_strain = np.zeros((self.num_nodes*self.dim, self.dim, self.time_steps),dtype=np.float64)        
        for t_n in range(1, self.time_steps):
            for i in range(0, self.num_nodes):
                for j in range(0, self.dim):
                    for r in range(0, self.dim):                    
                        self.global_strain[i*self.dim+r,j,t_n] = self.strain_tensor(problem, i, t_n)[r,j]
        
#    # Return the stress tensor related to node i
#    def stress_tensor(self, problem, i, t_n):
#        stress = np.zeros((self.dim, self.dim),dtype=np.float64)
#        for h in range(0, self.dim):
#            for j in range(0, self.dim):
#                for k in range(0, self.dim):
#                    for l in range(0, self.dim):
#                        stress[h,j] += self.C[h,j,k,l] * self.strain_tensor(problem, i, t_n)[k,l]
#                        
#        return stress
#
#    # Return the stress tensor for each node
#    def global_stress_tensor(self, problem):
#        self.global_stress = np.zeros((self.num_nodes*self.dim, self.dim, self.time_steps),dtype=np.float64)        
#        for t_n in range(1, self.time_steps):
#            for i in range(0, self.num_nodes):
#                for j in range(0, self.dim):
#                    for r in range(0, self.dim):                    
#                        self.global_stress[i*self.dim+r,j,t_n] = self.stress_tensor(problem, i, t_n)[r,j]            
            
        