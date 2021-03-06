import numpy as np
from scipy.linalg import expm
import multiprocess as mp
from scipy.special import comb
from ilsmc.get_ABC import get_ABC, get_ABC_inf_bis
from ilsmc.vanloan import vanloan_1, vanloan_2, vanloan_3, instant_mat
from ilsmc.get_times import get_times
from ilsmc.get_ordered import get_ordered

def precomp(trans_mat, times):
    dct = {}
    for i in range(len(times)):
        dct[i] = expm(trans_mat*times[i])
    return dct

def get_ABC_precomp(dct, omegas):
    """
    This function calculates the joint probabilities
    for the two-sequence CTMC.
    
    Parameters
    ----------
    trans_mat : numpy array
        The transition rate matrix of the two-sequence CTMC
    times : list of numbers
        Time intervals for each matrix multiplication
    omegas : list of lists
        Sets of states for each matrix multiplication
    """
    # Calculate first multiplication
    g = dct[0][omegas[0]][:,omegas[1]]
    # For each of the remaining omegas
    for i in range(1, len(dct)):
        # Perform multiplication
        g = g @ dct[i][omegas[i]][:,omegas[i+1]]
    # Return a numpy array that contains the probabilities in the right order.
    return g

def get_tab_AB(state_space_AB, trans_mat_AB, cut_AB, pi_AB):
    """
    This functions returns a table with joint probabilities of
    the end probabilities per state after running a two-sequence
    CTMC segregated by the fate of each pair of sites. 
    
    Parameters
    ----------
    state_space_AB : list of lists of tuples
        States of the whole state space two-sequence CTMC
    trans_mat_AB : numeric numpy matrix
        Transition rate matrix of the two-sequence CTMC
    cut_AB : list of floats
        Ordered cutpoints of the two-sequence CTMC
    pi_AB : list of floats
        Starting probabilities after merging two one-sequence CTMCs. 
    """
    tm = get_times(cut_AB, list(range(len(cut_AB))))
    pr = precomp(trans_mat_AB, tm)
    
    ###############################
    ### State-space information ###
    ###############################
    
    # Get flatten list of states, where even-indexed numbers (0, 2, ...)
    # represent the left-side coalescence states and odd-indexed numbers
    # (1, 3, ...) represent right-side coalescence.
    flatten = [list(sum(i, ())) for i in state_space_AB]
    # Get the index of all states where there is not a 2 (no coalescent)
    omega_B = [i for i in range(15) if 3 not in flatten[i]]
    # Get the index of all states where there is a 2 on left but not on right
    omega_L = [i for i in range(15) if (3 in flatten[i][::2]) and (3 not in flatten[i][1::2])]
    # Get the index of all states where there is a 2 on right but not on left
    omega_R = [i for i in range(15) if (3 not in flatten[i][::2]) and (3 in flatten[i][1::2])]
    # Get the index of all states where there is a 2 on left and right
    omega_E = [i for i in range(15) if (3 in flatten[i][::2]) and (3 in flatten[i][1::2])]
    # Get the index of all states
    omega_tot_AB = [i for i in range(15)]
    
        
    # Number of intervals
    n_int_AB = len(cut_AB)-1
    # Create empty table for the joint probabilities
    tab = np.zeros((n_int_AB*n_int_AB+n_int_AB*2+1, 15))
    # Create empty vector for the names of the states
    tab_names = []
    # Create accumulator for keeping track of the indices for the table
    acc = 0
    
    ############################################
    ### Deep coalescence -> deep coalescence ###
    ############################################
    
    # A pair of sites whose fate is to be of deep coalescence is represented as (('D'), ('D')).
    omegas = [omega_tot_AB]+[omega_B]*(n_int_AB)
    p_ABC = pi_AB @ get_ABC_precomp(pr, omegas)
    tab[acc] = get_ordered(p_ABC, omega_B, omega_tot_AB)
    tab_names.append((('D'), ('D')))
    acc += 1

    
    
    ##############################
    ### V0 -> deep coalescence ###
    ### Deep coalescence -> V0 ###
    ##############################
    
    # A pair of sites where the left site is in V0 and the right site is of deep coalescence
    # is represented as ((0, L), ('D')), where L is the index of the interval where the first
    # left coalescent happens. Remember that the probability of ((0, L) -> ('D')) is the same as
    # that of (('D'), (0, L)).
    for L in range(n_int_AB):
        omegas = [omega_tot_AB]+[omega_B]*L+[omega_L]*(n_int_AB-L)
        p_ABC = pi_AB @ get_ABC_precomp(pr, omegas)
        p_ABC = get_ordered(p_ABC, omega_L, omega_tot_AB)
        tab[acc] = p_ABC
        tab_names.append(((0, L), ('D')))
        tab[acc+1] = p_ABC
        tab_names.append((('D'), (0, L)))
        acc += 2
        
    
        
    ################
    ### V0 -> V0 ###
    ################    
    
    # A pair of sites whose fate is to be V0 states is represented as ((0, L), (0, R)), where
    # L is the index of the interval where the first left coalescent happens, and R is the same
    # for the first right coalescent. Remember that the probability of ((0, L) -> (0, R)) equals
    # that of ((0, R), (0, L)).
    for L in range(n_int_AB):
        for R in range(L, n_int_AB):
            if R == L:
                omegas = [omega_tot_AB]+[omega_B]*L+[omega_E]*(n_int_AB-L)
                p_ABC = pi_AB @ get_ABC_precomp(pr, omegas)
                tab[acc] = get_ordered(p_ABC, omega_E, omega_tot_AB)
                tab_names.append(((0, L), (0, R)))
                acc += 1

            elif L < R:
                omegas = [omega_tot_AB]+[omega_B]*L+[omega_L]*(R-L)+[omega_E]*(n_int_AB-R)
                p_ABC = pi_AB @ get_ABC_precomp(pr, omegas)
                p_ABC = get_ordered(p_ABC, omega_E, omega_tot_AB)
                tab[acc] = p_ABC
                tab_names.append(((0, L), (0, R)))
                tab[acc+1] = p_ABC
                tab_names.append(((0, R), (0, L)))
                acc += 2

                
    return tab_names, tab



def get_tab_ABC(state_space_ABC, trans_mat_ABC, cut_ABC, pi_ABC, names_tab_AB, n_int_AB):
    """
    This functions returns a table with joint probabilities of
    the states of the HMM after running a three-sequence CTMC
    
    Parameters
    ----------
    state_space_ABC : list of lists of tuples
        States of the whole state space of the three-sequence CTMC
    trans_mat_ABC : numeric numpy matrix
        Transition rate matrix of the three-sequence CTMC
    cut_ABC : list of floats
        Ordered cutpoints of the three-sequence CTMC
    pi_ABC : list of floats
        Starting probabilities after merging a one-sequence and a
        two-sequence CTMCs. 
    names_tab_AB : list of tuples
        List of fates for the starting probabilities, as outputted
        by get_tab_AB().
    n_int_AB : integer
        Number of intervals in the two-sequence CTMC
    """
    
    ###############################
    ### State-space information ###
    ###############################
    
    om = {}
    flatten = [list(sum(i, ())) for i in state_space_ABC]    
    for l in [0, 3, 5, 6, 7]:
        for r in [0, 3, 5, 6, 7]:
            if (l in [3, 5, 6, 7]) and (r in [3, 5, 6, 7]):
                om['%s%s' % (l, r)] = [i for i in range(203) if (l in flatten[i][::2]) and (r in flatten[i][1::2])]
            elif (l == 0) and (r in [3, 5, 6, 7]):
                om['%s%s' % (l, r)] = [i for i in range(203) if (all(x not in [3, 5, 6, 7] for x in flatten[i][::2])) and (r in flatten[i][1::2])]
            elif (l  in [3, 5, 6, 7]) and (r == 0):
                om['%s%s' % (l, r)] = [i for i in range(203) if (l in flatten[i][::2]) and (all(x not in [3, 5, 6, 7] for x in flatten[i][1::2]))]
            elif l == r == 0:
                om['%s%s' % (l, r)] = [i for i in range(203) if all(x not in [3, 5, 6, 7] for x in flatten[i])]
    omega_tot_ABC = [i for i in range(203)]
    om['71'] = sorted(om['73']+om['75']+om['76'])
    om['17'] = sorted(om['37']+om['57']+om['67'])
    om['10'] = sorted(om['30']+om['50']+om['60'])
    om['13'] = sorted(om['33']+om['53']+om['63'])
    om['15'] = sorted(om['35']+om['55']+om['65'])
    om['16'] = sorted(om['36']+om['56']+om['66'])
    om['11'] = sorted(om['13']+om['15']+om['16'])
    
    dct_num = {3:1, 5:2, 6:3}
    
    # Number of final states
    n_int_ABC = len(cut_ABC)-1
    n_markov_states = n_int_AB*n_int_ABC+n_int_ABC*3+3*comb(n_int_ABC, 2, exact = True)
    
    # Create empty transition probability matrix
    tab=np.empty((n_markov_states**2, 3), dtype=object)
    # Create accumulator for keeping track of the indices for the table
    acc_tot = 0
    
    
    
    ################
    ### V0 -> V0 ###
    ################
   
    # A pair of sites whose fate is to be V0 states is represented as ((0, l, L), (0, r, R)), where
    # l is the index of the interval where the first left coalescent happens, r is the same
    # for the first right coalescent, L is the same for the second left coalescent, and R is the 
    # second right coalescent. Remember that the probability of ((0, l, L) -> (0, r, R)) equals
    # that of ((0, r, R), (0, l, L)).
    for l in range(n_int_AB):
        for r in range(n_int_AB):
            cond = [i == ((0, l),(0, r)) for i in names_tab_AB]
            pi = pi_ABC[cond]
            for L in range(n_int_ABC):
                for R in range(n_int_ABC):
                    if L < R:                        
                        times_ABC = get_times(cut_ABC, [0, L, L+1, R, R+1])
                        omegas_ABC = [omega_tot_ABC, om['11'], om['71'], om['71'], om['77']]
                        p_ABC = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                        tab[acc_tot]   = [(0, l, L), (0, r, R), (pi@p_ABC).sum()]
                        tab[acc_tot+1] = [(0, r, R), (0, l, L), tab[acc_tot][2]]
                        acc_tot += 2
                    elif L == R:
                        times_ABC = get_times(cut_ABC, [0, L, L+1])
                        omegas_ABC = [omega_tot_ABC, om['11'], om['77']]
                        p_ABC = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                        tab[acc_tot] = [(0, l, L), (0, r, R), (pi@p_ABC).sum()]
                        acc_tot += 1
                    else:
                        continue
  
    
    ##############################
    ### V0 -> deep coalescence ###
    ### Deep coalescence -> V0 ###
    ##############################

    
    # A pair of sites where the left site is in V0 and the right site is of deep coalescence
    # is represented as ((0, l, L), (i, r, R)), where l is the index of the interval where the 
    # first left coalescent happens, L is the same for the second left coalescent, r is the 
    # same for the first right coalescent and R is the same for the second right coalescent. The index
    # i can take values from 1 to 4, where 1 to 3 represents deep coalescent and l < L, and 4 
    # represents a multiple merger event where l = L. Remember that the probability of 
    # ((0, l, L) -> (i, r, R)) and that of ((i, r, R) -> (0, l, L)) is the same. Also,
    # ((0, l, L) -> (1, r, R)) = ((0, l, L) -> (2, r, R)) = ((0, l, L) -> (3, r, R)), following ILS.
    
    for L in range(n_int_ABC):
        for r in range(n_int_ABC):
            for R in range(r, n_int_ABC):
                if L < r < R:
                    times_ABC = get_times(cut_ABC, [0, L, L+1, r, r+1, R, R+1])
                    omegas_ABC = [omega_tot_ABC, om['10'], om['70'], om['70']]
                    for i in [3, 5, 6]:
                        ii = dct_num[i]
                        omegas_ABC = omegas_ABC+[om['7%s'%i], om['7%s'%i], om['77']]
                        p_ABC = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                        for l in range(n_int_AB):
                            cond = [i == ((0, l), 'D') for i in names_tab_AB]
                            pi = pi_ABC[cond]
                            tab[acc_tot]   = [(0, l, L), (ii, r, R), (pi@p_ABC).sum()]
                            tab[acc_tot+1] = [(ii, r, R), (0, l, L), tab[acc_tot][2]]
                            acc_tot += 2
                elif L == r < R:
                    times_ABC = get_times(cut_ABC, [0, L, L+1, R, R+1])
                    omegas_ABC = [omega_tot_ABC, om['10']]
                    for i in [3, 5, 6]:
                        ii = dct_num[i]
                        omegas_ABC = omegas_ABC+[om['7%s'%i], om['7%s'%i], om['77']]
                        p_ABC = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                        for l in range(n_int_AB):
                            cond = [i == ((0, l), 'D') for i in names_tab_AB]
                            pi = pi_ABC[cond]
                            tab[acc_tot]   = [(0, l, L), (ii, r, R), (pi@p_ABC).sum()]
                            tab[acc_tot+1] = [(ii, r, R), (0, l, L), tab[acc_tot][2]]
                            acc_tot += 2
                elif r < L < R:
                    times_ABC = get_times(cut_ABC, [0, r, r+1, L, L+1, R, R+1])
                    omegas_ABC = [omega_tot_ABC, om['10']]
                    for i in [3, 5, 6]:
                        ii = dct_num[i]
                        omegas_ABC = omegas_ABC+[om['1%s'%i], om['1%s'%i], om['7%s'%i], om['7%s'%i], om['77']]
                        p_ABC = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                        for l in range(n_int_AB):
                            cond = [i == ((0, l), 'D') for i in names_tab_AB]
                            pi = pi_ABC[cond]
                            tab[acc_tot]   = [(0, l, L), (ii, r, R), (pi@p_ABC).sum()]
                            tab[acc_tot+1] = [(ii, r, R), (0, l, L), tab[acc_tot][2]]
                            acc_tot += 2
                elif r < L == R:
                    times_ABC = get_times(cut_ABC, [0, r, r+1, L, L+1])
                    omegas_ABC = [omega_tot_ABC, om['10']]
                    for i in [3, 5, 6]:
                        ii = dct_num[i]
                        omegas_ABC = omegas_ABC+[om['1%s'%i], om['1%s'%i], om['77']]
                        p_ABC = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                        for l in range(n_int_AB):
                            cond = [i == ((0, l), 'D') for i in names_tab_AB]
                            pi = pi_ABC[cond]
                            tab[acc_tot]   = [(0, l, L), (ii, r, R), (pi@p_ABC).sum()]
                            tab[acc_tot+1] = [(ii, r, R), (0, l, L), tab[acc_tot][2]]
                            acc_tot += 2
                elif r < R < L:
                    times_ABC = get_times(cut_ABC, [0, r, r+1, R, R+1, L, L+1])
                    omegas_ABC = [omega_tot_ABC, om['10']]
                    for i in [3, 5, 6]:
                        ii = dct_num[i]
                        omegas_ABC = omegas_ABC+[om['1%s'%i], om['1%s'%i], om['17'], om['17'], om['77']]
                        p_ABC = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                        for l in range(n_int_AB):
                            cond = [i == ((0, l), 'D') for i in names_tab_AB]
                            pi = pi_ABC[cond]
                            tab[acc_tot]   = [(0, l, L), (ii, r, R), (pi@p_ABC).sum()]
                            tab[acc_tot+1] = [(ii, r, R), (0, l, L), tab[acc_tot][2]]
                            acc_tot += 2
                elif L < r == R:
                    omegas_ABC = [omega_tot_ABC, om['10'], om['70'], om['70']]
                    times_ABC = get_times(cut_ABC, [0, L, L+1, r])
                    p_ABC = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                    for i in [3, 5, 6]:
                        if cut_ABC[r+1] != np.inf:
                            res = vanloan_1(
                                trans_mat_ABC, (om['70'], om['7%s'%i]),
                                om['70'], om['77'], cut_ABC[r+1]-cut_ABC[r])
                        else:
                            A_mat = instant_mat(om['70'], om['7%s'%i], trans_mat_ABC)
                            res = (-np.linalg.inv(trans_mat_ABC[:-2,:-2])@(A_mat[:-2,:-2]))[om['70']][:,om['7%s'%i]]
                        for l in range(n_int_AB):
                            cond = [i == ((0, l), 'D') for i in names_tab_AB]
                            pi = pi_ABC[cond]
                            ii = dct_num[i]
                            tab[acc_tot]   = [(0, l, L), (ii, r, R), (pi@p_ABC@res).sum()]
                            tab[acc_tot+1] = [(ii, r, R), (0, l, L), tab[acc_tot][2]]
                            acc_tot += 2
                elif L == r == R:
                    omegas_ABC = [omega_tot_ABC, om['10']]
                    times_ABC = get_times(cut_ABC, [0, L])
                    p_ABC = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                    for i in [3, 5, 6]:
                        if cut_ABC[r+1] == np.inf:
                            A_mat = instant_mat(om['10'], om['1%s'%i], trans_mat_ABC)
                            res_1 = (-np.linalg.inv(trans_mat_ABC[:-2,:-2])@(A_mat[:-2,:-2]))[om['10']][:,om['1%s'%i]]
                            A_mat = instant_mat(om['10'], om['7%s'%i], trans_mat_ABC)
                            res_2 = (-np.linalg.inv(trans_mat_ABC[:-2,:-2])@(A_mat[:-2,:-2]))[om['10']][:,om['7%s'%i]]
                            A_mat_1 = instant_mat(om['10'], om['70'], trans_mat_ABC)
                            A_mat_2 = instant_mat(om['70'], om['7%s'%i], trans_mat_ABC)
                            C_mat_upper =  np.concatenate((trans_mat_ABC[:-2,:-2], A_mat_1[:-2,:-2]), axis = 1)
                            C_mat_lower = np.concatenate((np.zeros((201,201)), trans_mat_ABC[:-2,:-2]), axis = 1)
                            C_mat = np.concatenate((C_mat_upper, C_mat_lower), axis = 0)
                            res_3 = ((-np.linalg.inv(C_mat)[0:201,-201:])@(A_mat_2[:-2,:-2]))[om['10']][:,om['7%s'%i]]
                            for l in range(n_int_AB):
                                cond = [i == ((0, l), 'D') for i in names_tab_AB]
                                pi = pi_ABC[cond]
                                ii = dct_num[i]
                                tab[acc_tot]   = [(0, l, L), (ii, r, R), (pi@p_ABC@res_1).sum()+(pi@p_ABC@sum([res_2, res_3])).sum()]
                                tab[acc_tot+1] = [(ii, r, R), (0, l, L), tab[acc_tot][2]]
                                acc_tot += 2
                        else:
                            omega_lst = ['10', '1%s'%i, '17', '70', '7%s'%i, '77']
                            iter_lst = []
                            for y in range(1, len(omega_lst)):
                                for z in range(y+1, len(omega_lst)):
                                    tup = (om['%s'%(omega_lst[0],)], 
                                            om['%s'%(omega_lst[y],)],
                                            om['%s'%(omega_lst[z],)])
                                    iter_lst.append(tup)
                            pool = mp.Pool(mp.cpu_count())
                            res_tot = []
                            res_tot = pool.starmap_async(
                                vanloan_2, 
                                [(trans_mat_ABC, tup, om['10'],
                                    om['77'], cut_ABC[r+1]-cut_ABC[r]) for tup in iter_lst]
                            ).get()
                            pool.close()
                            for l in range(n_int_AB):
                                cond = [i == ((0, l), 'D') for i in names_tab_AB]
                                pi = pi_ABC[cond]
                                ii = dct_num[i]
                                tab[acc_tot]   = [(0, l, L), (ii, r, R), (pi@p_ABC@sum(res_tot)).sum()]
                                tab[acc_tot+1] = [(ii, r, R), (0, l, L), (pi@p_ABC@sum(res_tot)).sum()]
                                acc_tot += 2
                elif r == R < L:
                    omegas_ABC = [omega_tot_ABC, om['10']]
                    times_ABC = get_times(cut_ABC, [0, r])
                    p_ABC_start = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                    omegas_ABC = [om['17'], om['17'], om['77']]
                    times_ABC = get_times(cut_ABC, [r+1, L, L+1])
                    p_ABC_end = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                    for i in [3, 5, 6]:
                        A_mat = instant_mat(om['10'], om['1%s'%i], trans_mat_ABC)
                        C_mat_upper = np.concatenate((trans_mat_ABC, A_mat), axis = 1)
                        C_mat_lower = np.concatenate((np.zeros((203,203)), trans_mat_ABC), axis = 1)
                        C_mat = np.concatenate((C_mat_upper, C_mat_lower), axis = 0)
                        res = (expm(C_mat*(cut_ABC[r+1]-cut_ABC[r]))[:203,-203:])[om['10']][:,om['17']]
                        for l in range(n_int_AB):
                            cond = [i == ((0, l), 'D') for i in names_tab_AB]
                            pi = pi_ABC[cond]
                            ii = dct_num[i]
                            tab[acc_tot]   = [(0, l, L), (ii, r, R), (pi@p_ABC_start@res@p_ABC_end).sum()]
                            tab[acc_tot+1] = [(ii, r, R), (0, l, L), tab[acc_tot][2]]
                            acc_tot += 2        
                else:
                    continue
                        
    ############################################
    ### Deep coalescence -> deep coalescence ###
    ############################################
    
    # A pair of sites where both the left and the right site are of deep coalescence is 
    # represented as ((i, l, L), (j, r, R)), where l is the index of the interval where the 
    # first left coalescent happens, L is the same for the second left coalescent, r is the 
    # same for the first right coalescent and R is the same for the second right coalescent.
    # The indices i and j can take values from 1 to 4, where 1 to 3 represents deep coalescent 
    # and l < L, and 4  represents a multiple merger event where l = L. Remember that the probability 
    # of ((i, l, L) -> (j, r, R)) and that of ((j, r, R) -> (i, l, L)) is the same. Also,
    # ((i, l, L) -> (1, r, R)) = ((i, l, L) -> (2, r, R)) = ((i, l, L) -> (3, r, R)), following ILS.
    cond = [i == ('D','D') for i in names_tab_AB]
    pi = pi_ABC[cond]
    for l in range(n_int_ABC):
        for L in range(l, n_int_ABC):
            for r in range(n_int_ABC):
                for R in range(r, n_int_ABC): 
                    if l < L < r < R:
                        times_ABC = get_times(cut_ABC, [0, l, l+1, L, L+1, r, r+1, R, R+1])
                        for i in [3, 5, 6]:
                            for j in [3, 5, 6]:
                                # 00 -> i0 -> 70 -> 7j -> 77
                                omegas_ABC = [omega_tot_ABC, om['00'], 
                                              om['%s0'%i], om['%s0'%i], 
                                              om['70'], om['70'], 
                                              om['7%s'%j], om['7%s'%j], 
                                              om['77']]
                                p_ABC = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                                ii = dct_num[i]
                                jj = dct_num[j]
                                tab[acc_tot]   = [(ii, l, L), (jj, r, R), (pi@p_ABC).sum()]
                                tab[acc_tot+1] = [(jj, r, R), (ii, l, L), tab[acc_tot][2]]
                                acc_tot += 2
                    elif l < L == r < R:
                        times_ABC = get_times(cut_ABC, [0, l, l+1, L, L+1, R, R+1])
                        for i in [3, 5, 6]:
                            for j in [3, 5, 6]:
                                # 00 -> i0 -> 7j -> 77
                                omegas_ABC = [omega_tot_ABC, om['00'], 
                                              om['%s0'%i], om['%s0'%i], 
                                              om['7%s'%j], om['7%s'%j], 
                                              om['77']]
                                p_ABC = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                                ii = dct_num[i]
                                jj = dct_num[j]
                                tab[acc_tot]   = [(ii, l, L), (jj, r, R), (pi@p_ABC).sum()]
                                tab[acc_tot+1] = [(jj, r, R), (ii, l, L), tab[acc_tot][2]]
                                acc_tot += 2
                    elif l == r < L < R:
                        times_ABC = get_times(cut_ABC, [0, l, l+1, L, L+1, R, R+1])
                        for i in [3, 5, 6]:
                            for j in [3, 5, 6]:
                                # 00 -> ij -> 7j -> 77
                                omegas_ABC = [omega_tot_ABC, om['00'], 
                                              om['%s%s'%(i,j)], om['%s%s'%(i,j)], 
                                              om['7%s'%j], om['7%s'%j], 
                                              om['77']]
                                p_ABC = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                                ii = dct_num[i]
                                jj = dct_num[j]
                                tab[acc_tot]   = [(ii, l, L), (jj, r, R), (pi@p_ABC).sum()]
                                tab[acc_tot+1] = [(jj, r, R), (ii, l, L), tab[acc_tot][2]]
                                acc_tot += 2
                    elif l < r < L < R:
                        times_ABC = get_times(cut_ABC, [0, l, l+1, r, r+1, L, L+1, R, R+1])
                        for i in [3, 5, 6]:
                            for j in [3, 5, 6]:
                                # 00 -> i0 -> ij -> 7j -> 77
                                omegas_ABC = [omega_tot_ABC, om['00'], 
                                              om['%s0'%i], om['%s0'%i], 
                                              om['%s%s'%(i,j)], om['%s%s'%(i,j)],
                                              om['7%s'%j], om['7%s'%j], 
                                              om['77']]
                                p_ABC = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                                ii = dct_num[i]
                                jj = dct_num[j]
                                tab[acc_tot]   = [(ii, l, L), (jj, r, R), (pi@p_ABC).sum()]
                                tab[acc_tot+1] = [(jj, r, R), (ii, l, L), tab[acc_tot][2]]
                                acc_tot += 2
                    elif r < l < L < R:
                        times_ABC = get_times(cut_ABC, [0, r, r+1, l, l+1, L, L+1, R, R+1])
                        for i in [3, 5, 6]:
                            for j in [3, 5, 6]:
                                # 00 -> 0j -> ij -> 7j -> 77
                                omegas_ABC = [omega_tot_ABC, om['00'], 
                                              om['0%s'%j], om['0%s'%j], 
                                              om['%s%s'%(i,j)], om['%s%s'%(i,j)],
                                              om['7%s'%j], om['7%s'%j], 
                                              om['77']]
                                p_ABC = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                                ii = dct_num[i]
                                jj = dct_num[j]
                                tab[acc_tot]   = [(ii, l, L), (jj, r, R), (pi@p_ABC).sum()]
                                tab[acc_tot+1] = [(jj, r, R), (ii, l, L), tab[acc_tot][2]]
                                acc_tot += 2
                    elif l == r < L == R:
                        times_ABC = get_times(cut_ABC, [0, l, l+1, L, L+1])
                        for i in [3, 5, 6]:
                            for j in [3, 5, 6]:
                                # 00 -> ij -> 77
                                omegas_ABC = [omega_tot_ABC, om['00'], 
                                              om['%s%s'%(i,j)], om['%s%s'%(i,j)],
                                              om['77']]
                                p_ABC = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                                
                                ii = dct_num[i]
                                jj = dct_num[j]                                
                                tab[acc_tot]   = [(ii, l, L), (jj, r, R), (pi@p_ABC).sum()]
                                acc_tot += 1
                    elif l < r < L == R:
                        times_ABC = get_times(cut_ABC, [0, l, l+1, r, r+1, L, L+1])
                        for i in [3, 5, 6]:
                            for j in [3, 5, 6]:
                                # 00 -> i0 -> ij -> 77
                                omegas_ABC = [omega_tot_ABC, om['00'], 
                                              om['%s0'%i], om['%s0'%i], 
                                              om['%s%s'%(i,j)], om['%s%s'%(i,j)],
                                              om['77']]
                                p_ABC = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                                ii = dct_num[i]
                                jj = dct_num[j]
                                tab[acc_tot]   = [(ii, l, L), (jj, r, R), (pi@p_ABC).sum()]
                                tab[acc_tot+1] = [(jj, r, R), (ii, l, L), tab[acc_tot][2]]
                                acc_tot += 2
                    elif l == r == L == R:
                        times_ABC = get_times(cut_ABC, [0, l, l+1])
                        omegas_ABC = [omega_tot_ABC, om['00'], om['77']]
                        p_ABC = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                        times_ABC = get_times(cut_ABC, [0, l])
                        omegas_ABC = [omega_tot_ABC, om['00']]
                        start = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                        for i in [3, 5, 6]:
                            for j in [3, 5, 6]:
                                res_tot = 0
                                if cut_ABC[r+1] == np.inf:
                                    res_tot = 0
                                    # 00 -> ij
                                    A_mat = instant_mat(om['00'], om['%s%s'%(i,j)], trans_mat_ABC)
                                    res_1 = (-np.linalg.inv(trans_mat_ABC[:-2,:-2])@(A_mat[:-2,:-2]))[om['00']][:,om['%s%s'%(i,j)]]
                                    # 00 -> i0 -> ij
                                    A_mat_1 = instant_mat(om['00'], om['%s0'%i], trans_mat_ABC)
                                    A_mat_2 = instant_mat(om['%s0'%i], om['%s%s'%(i,j)], trans_mat_ABC)
                                    C_mat_upper =  np.concatenate((trans_mat_ABC[:-2,:-2], A_mat_1[:-2,:-2]), axis = 1)
                                    C_mat_lower = np.concatenate((np.zeros((201,201)), trans_mat_ABC[:-2,:-2]), axis = 1)
                                    C_mat = np.concatenate((C_mat_upper, C_mat_lower), axis = 0)
                                    res_2 = ((-np.linalg.inv(C_mat)[0:201,-201:])@(A_mat_2[:-2,:-2]))[om['00']][:,om['%s%s'%(i,j)]]
                                    # 00 -> 0j -> ij
                                    A_mat_1 = instant_mat(om['00'], om['0%s'%j], trans_mat_ABC)
                                    A_mat_2 = instant_mat(om['0%s'%j], om['%s%s'%(i,j)], trans_mat_ABC)
                                    C_mat_upper =  np.concatenate((trans_mat_ABC[:-2,:-2], A_mat_1[:-2,:-2]), axis = 1)
                                    C_mat_lower = np.concatenate((np.zeros((201,201)), trans_mat_ABC[:-2,:-2]), axis = 1)
                                    C_mat = np.concatenate((C_mat_upper, C_mat_lower), axis = 0)
                                    res_3 = ((-np.linalg.inv(C_mat)[0:201,-201:])@(A_mat_2[:-2,:-2]))[om['00']][:,om['%s%s'%(i,j)]]
                                    # 00 -> 0j -> 07 -> i7
                                    A_mat_1 = instant_mat(om['00'], om['0%s'%j], trans_mat_ABC)
                                    A_mat_2 = instant_mat(om['0%s'%j], om['07'], trans_mat_ABC)
                                    A_mat_3 = instant_mat(om['07'], om['%s7'%i], trans_mat_ABC)
                                    C_mat_upper  =  np.concatenate((trans_mat_ABC[:-2,:-2], A_mat_1[:-2,:-2], np.zeros((201,201))), axis = 1)
                                    C_mat_middle =  np.concatenate((np.zeros((201,201)), trans_mat_ABC[:-2,:-2], A_mat_2[:-2,:-2]), axis = 1)
                                    C_mat_lower  =  np.concatenate((np.zeros((201,201)),np.zeros((201,201)), trans_mat_ABC[:-2,:-2]), axis = 1)
                                    C_mat = np.concatenate((C_mat_upper, C_mat_middle, C_mat_lower), axis = 0)
                                    res_4 = ((-np.linalg.inv(C_mat)[0:201,-201:])@(A_mat_3[:-2,:-2]))[om['00']][:,om['%s7'%i]]
                                    # 00 -> i0 -> 70 -> 7j
                                    A_mat_1 = instant_mat(om['00'], om['%s0'%i], trans_mat_ABC)
                                    A_mat_2 = instant_mat(om['%s0'%i], om['70'], trans_mat_ABC)
                                    A_mat_3 = instant_mat(om['70'], om['7%s'%j], trans_mat_ABC)
                                    C_mat_upper  =  np.concatenate((trans_mat_ABC[:-2,:-2], A_mat_1[:-2,:-2], np.zeros((201,201))), axis = 1)
                                    C_mat_middle =  np.concatenate((np.zeros((201,201)), trans_mat_ABC[:-2,:-2], A_mat_2[:-2,:-2]), axis = 1)
                                    C_mat_lower  =  np.concatenate((np.zeros((201,201)), np.zeros((201,201)), trans_mat_ABC[:-2,:-2]), axis = 1)
                                    C_mat = np.concatenate((C_mat_upper, C_mat_middle, C_mat_lower), axis = 0)
                                    res_5 = ((-np.linalg.inv(C_mat)[0:201,-201:])@(A_mat_3[:-2,:-2]))[om['00']][:,om['7%s'%j]]                               
                                    # 00 -> 0j -> j7
                                    A_mat_1 = instant_mat(om['00'], om['0%s'%j], trans_mat_ABC)
                                    A_mat_2 = instant_mat(om['0%s'%j], om['%s7'%i], trans_mat_ABC)
                                    C_mat_upper =  np.concatenate((trans_mat_ABC[:-2,:-2], A_mat_1[:-2,:-2]), axis = 1)
                                    C_mat_lower = np.concatenate((np.zeros((201,201)), trans_mat_ABC[:-2,:-2]), axis = 1)
                                    C_mat = np.concatenate((C_mat_upper, C_mat_lower), axis = 0)
                                    res_6 = ((-np.linalg.inv(C_mat)[0:201,-201:])@(A_mat_2[:-2,:-2]))[om['00']][:,om['%s7'%i]]
                                    # 00 -> i0 -> 7j
                                    A_mat_1 = instant_mat(om['00'], om['%s0'%i], trans_mat_ABC)
                                    A_mat_2 = instant_mat(om['%s0'%i], om['7%s'%j], trans_mat_ABC)
                                    C_mat_upper =  np.concatenate((trans_mat_ABC[:-2,:-2], A_mat_1[:-2,:-2]), axis = 1)
                                    C_mat_lower = np.concatenate((np.zeros((201,201)), trans_mat_ABC[:-2,:-2]), axis = 1)
                                    C_mat = np.concatenate((C_mat_upper, C_mat_lower), axis = 0)
                                    res_7 = ((-np.linalg.inv(C_mat)[0:201,-201:])@(A_mat_2[:-2,:-2]))[om['00']][:,om['7%s'%j]]
                                    # Sum results
                                    res_tot += (pi@start@sum([res_1, res_2, res_3])).sum()
                                    res_tot += (pi@start@sum([res_4, res_6])).sum()
                                    res_tot += (pi@start@sum([res_5, res_7])).sum()
                                    ii = dct_num[i]
                                    jj = dct_num[j]
                                    tab[acc_tot] = [(ii, l, L), (jj, r, R), res_tot]
                                    acc_tot += 1
                                else:
                                    iter_lst = []
                                    for y in ['%s0'%i, '0%s'%j]:
                                        for z in ['%s7'%i, '7%s'%j]:
                                            tup = (om['00'], 
                                                   om['%s'%(y,)],
                                                   om['%s'%(z,)],
                                                   om['77'])
                                            iter_lst.append(tup)
                                    for y in ['%s%s'%(i,j)]:
                                        for z in ['%s7'%i, '7%s'%j]:
                                            tup = (om['00'], 
                                               om['%s'%(y,)],
                                               om['%s'%(z,)],
                                               om['77'])
                                            iter_lst.append(tup)
                                    for y in ['%s0'%i, '0%s'%j]:
                                        for z in ['%s%s'%(i,j), '70', '07']:
                                            if (int(y[0])-int(z[0]))==-7 or (int(y[1])-int(z[1]))==-7:
                                                continue
                                            for v in ['%s7'%i, '7%s'%j, '77']:
                                                if (int(z[0]) > int(v[0])) or (int(z[1]) > int(v[1])):
                                                    continue
                                                if (int(z[0])-int(v[0]))==-7 or (int(z[1])-int(v[1]))==-7:
                                                    continue
                                                tup = (om['00'], 
                                                       om['%s'%(y,)],
                                                       om['%s'%(z,)],
                                                       om['%s'%(v,)])
                                                iter_lst.append(tup)
                                    pool = mp.Pool(mp.cpu_count())
                                    res_iter = []
                                    res_iter = pool.starmap_async(
                                        vanloan_3, 
                                        [(trans_mat_ABC, tup, om['00'], om['77'],
                                          cut_ABC[r+1]-cut_ABC[r]) for tup in iter_lst]
                                    ).get()
                                    pool.close()
                                    res_tot += (pi@start@sum(res_iter)).sum()
                                    res_test = vanloan_2(
                                        trans_mat_ABC, 
                                        (om['00'], om['%s%s'%(i,j)], om['77']),
                                        om['00'], om['77'],
                                        cut_ABC[r+1]-cut_ABC[r]
                                    )
                                    res_tot += (pi@start@res_test).sum()
                                    ii = dct_num[i]
                                    jj = dct_num[j]
                                    tab[acc_tot] = [(ii, l, L), (jj, r, R), res_tot]
                                    acc_tot += 1
                    elif l == L < r == R:
                        times_ABC = get_times(cut_ABC, [0, l])
                        omegas_ABC = [omega_tot_ABC, om['00']]
                        start = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                        times_ABC = get_times(cut_ABC, [l+1, r])
                        omegas_ABC = [om['70'], om['70']]
                        end = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                        for i in [3, 5, 6]:
                            res_1 = vanloan_1(
                                trans_mat_ABC, 
                                (om['00'], om['%s0'%i]),
                                om['00'], om['70'], cut_ABC[l+1]-cut_ABC[l])
                            for j in [3, 5, 6]:
                                # 00 -> 0i -> 70 -> 7j
                                if cut_ABC[r+1] == np.inf:
                                    A_mat = instant_mat(om['70'], om['7%s'%j], trans_mat_ABC)
                                    res_2 = (-np.linalg.inv(trans_mat_ABC[:-2,:-2])@(A_mat[:-2,:-2]))[om['70']][:,om['7%s'%j]]
                                    ii = dct_num[i]
                                    jj = dct_num[j]
                                    tab[acc_tot] = [(ii, l, L), (jj, r, R), (pi@start@res_1@end@res_2).sum()]
                                    acc_tot += 1
                                    tab[acc_tot] = [(jj, r, R), (ii, l, L), tab[acc_tot-1][2]]
                                    acc_tot += 1
                                else:
                                    res_2 = vanloan_1(
                                        trans_mat_ABC,
                                        (om['70'], om['7%s'%j]),
                                        om['70'], om['77'], cut_ABC[r+1]-cut_ABC[r])
                                    ii = dct_num[i]
                                    jj = dct_num[j]
                                    tab[acc_tot] = [(ii, l, L), (jj, r, R), (pi@start@res_1@end@res_2).sum()]
                                    acc_tot += 1
                                    tab[acc_tot] = [(jj, r, R), (ii, l, L), tab[acc_tot-1][2]]
                                    acc_tot += 1
                    elif l == L < r < R:
                        for j in [3, 5, 6]:
                            times_ABC = get_times(cut_ABC, [0, l])
                            omegas_ABC = [omega_tot_ABC, om['00']]
                            start = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                            times_ABC = get_times(cut_ABC, [l+1, r, r+1, R, R+1])
                            omegas_ABC = [om['70'], om['70'],
                                          om['7%s'%j], om['7%s'%j], 
                                          om['77']]
                            end = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                            for i in [3, 5, 6]:
                                # 00 -> i0 -> 70 -> 7j
                                res = vanloan_1(
                                        trans_mat_ABC,
                                        (om['00'], om['%s0'%i]),
                                        om['00'], om['70'],
                                        cut_ABC[l+1]-cut_ABC[l])
                                ii = dct_num[i]
                                jj = dct_num[j]
                                tab[acc_tot] = [(ii, l, L), (jj, r, R), (pi@start@res@end).sum()]
                                acc_tot += 1
                                tab[acc_tot] = [(jj, r, R), (ii, l, L), tab[acc_tot-1][2]]
                                acc_tot += 1
                    elif l == L == r < R:
                        for j in [3, 5, 6]:
                            for i in [3, 5, 6]:
                                times_ABC = get_times(cut_ABC, [0, l])
                                omegas_ABC = [omega_tot_ABC, om['00']]
                                start = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                                times_ABC = get_times(cut_ABC, [l+1, R, R+1])
                                omegas_ABC = [om['7%s'%j], om['7%s'%j],
                                              om['77']]
                                end = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                                omega_lst = ['00', '%s0'%i, '0%s'%j, '%s%s'%(i,j), '70', '7%s'%j]
                                iter_lst = []
                                for y in range(1, len(omega_lst)):
                                    for z in range(y+1, len(omega_lst)):
                                        tup = (om['%s'%(omega_lst[0],)], 
                                               om['%s'%(omega_lst[y],)],
                                               om['%s'%(omega_lst[z],)])
                                        iter_lst.append(tup)
                                pool = mp.Pool(mp.cpu_count())
                                res_tot = []
                                res_tot = pool.starmap_async(
                                    vanloan_2, 
                                    [(trans_mat_ABC, tup, om['00'], om['7%s'%j],
                                      cut_ABC[r+1]-cut_ABC[r]) for tup in iter_lst]
                                ).get()
                                pool.close()
                                res_tot = (pi@start@sum(res_tot)@end).sum()
                                ii = dct_num[i]
                                jj = dct_num[j]
                                tab[acc_tot] = [(ii, l, L), (jj, r, R), res_tot]
                                acc_tot += 1
                                tab[acc_tot] = [(jj, r, R), (ii, l, L), res_tot]
                                acc_tot += 1
                    elif l < L == r == R:
                        for i in [3, 5, 6]:
                            times_ABC = get_times(cut_ABC, [0, l, l+1, L])
                            omegas_ABC = [omega_tot_ABC, om['00'], 
                                      om['%s0'%i], om['%s0'%i]]
                            p_ABC = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                            for j in [3, 5, 6]:
                                if cut_ABC[L+1] == np.inf:
                                    # 00 -> i0 -> 1j
                                    A_mat = instant_mat(om['%s0'%i], om['1%s'%j], trans_mat_ABC)
                                    res_1 = (-np.linalg.inv(trans_mat_ABC[:-2,:-2])@(A_mat[:-2,:-2]))[om['%s0'%i]][:,om['1%s'%j]]
                                    # 00 -> i0 -> 7j
                                    A_mat = instant_mat(om['%s0'%i], om['7%s'%j], trans_mat_ABC)
                                    res_2 = (-np.linalg.inv(trans_mat_ABC[:-2,:-2])@(A_mat[:-2,:-2]))[om['%s0'%i]][:,om['7%s'%j]]
                                    # 00 -> i0 -> 70 -> 7j
                                    A_mat_1 = instant_mat(om['%s0'%i], om['70'], trans_mat_ABC)
                                    A_mat_2 = instant_mat(om['70'], om['7%s'%j], trans_mat_ABC)
                                    C_mat_upper =  np.concatenate((trans_mat_ABC[:-2,:-2], A_mat_1[:-2,:-2]), axis = 1)
                                    C_mat_lower = np.concatenate((np.zeros((201,201)), trans_mat_ABC[:-2,:-2]), axis = 1)
                                    C_mat = np.concatenate((C_mat_upper, C_mat_lower), axis = 0)
                                    res_3 = ((-np.linalg.inv(C_mat)[0:201,-201:])@(A_mat_2[:-2,:-2]))[om['%s0'%i]][:,om['7%s'%j]]
                                    # Sum of results
                                    ii = dct_num[i]
                                    jj = dct_num[j]
                                    tab[acc_tot] = [(ii, l, L), (jj, r, R), (pi@p_ABC@res_1).sum()+(pi@p_ABC@sum([res_2, res_3])).sum()]
                                    acc_tot += 1
                                    tab[acc_tot] = [(jj, r, R), (ii, l, L), tab[acc_tot-1][2]]
                                    acc_tot += 1
                                else:
                                    omega_lst = ['%s0'%i, '%s%s'%(i,j), '%s7'%i, '70', '7%s'%j, '77']
                                    iter_lst = []
                                    for y in range(1, len(omega_lst)):
                                        for z in range(y+1, len(omega_lst)):
                                            tup = (om['%s'%(omega_lst[0],)], 
                                                   om['%s'%(omega_lst[y],)],
                                                   om['%s'%(omega_lst[z],)])
                                            iter_lst.append(tup)
                                    pool = mp.Pool(mp.cpu_count())
                                    res_tot = []
                                    res_tot = pool.starmap_async(
                                        vanloan_2, 
                                        [(trans_mat_ABC, tup, om['%s0'%i],
                                          om['77'], cut_ABC[r+1]-cut_ABC[r]) for tup in iter_lst]
                                    ).get()
                                    pool.close()
                                    res_tot = (pi@p_ABC@sum(res_tot)).sum()
                                    ii = dct_num[i]
                                    jj = dct_num[j]
                                    tab[acc_tot] = [(ii, l, L), (jj, r, R), res_tot]
                                    acc_tot += 1
                                    tab[acc_tot] = [(jj, r, R), (ii, l, L), res_tot]
                                    acc_tot += 1
                    elif l < L < r == R:
                        for i in [3, 5, 6]:
                            for j in [3, 5, 6]:
                                # 00 -> 70 -> 7j
                                times_ABC = get_times(cut_ABC, [0, l, l+1, L, L+1, r])
                                omegas_ABC = [omega_tot_ABC, om['00'], 
                                              om['%s0'%i], om['%s0'%i], 
                                              om['70'], om['70']]
                                p_ABC = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                                if cut_ABC[r+1] != np.inf:
                                    res = vanloan_1(
                                        trans_mat_ABC,
                                        (om['70'], om['7%s'%j]),
                                        om['70'], om['77'],
                                        cut_ABC[r+1]-cut_ABC[r])
                                    ii = dct_num[i]
                                    jj = dct_num[j]
                                    tab[acc_tot]   = [(ii, l, L), (jj, r, R), (pi@p_ABC@res).sum()]
                                    tab[acc_tot+1] = [(jj, r, R), (ii, l, L), tab[acc_tot][2]]
                                    acc_tot += 2
                                else:
                                    A_mat = instant_mat(om['70'], om['7%s'%j], trans_mat_ABC)
                                    res = (-np.linalg.inv(trans_mat_ABC[:-2,:-2])@(A_mat[:-2,:-2]))[om['70']][:,om['7%s'%j]]
                                    ii = dct_num[i]
                                    jj = dct_num[j]
                                    tab[acc_tot] = [(ii, l, L), (jj, r, R), (pi@p_ABC@res).sum()]
                                    acc_tot += 1
                                    tab[acc_tot] = [(jj, r, R), (ii, l, L), tab[acc_tot-1][2]]
                                    acc_tot += 1
                    elif r < l == L < R:
                        for j in [3, 5, 6]:
                            times_ABC = get_times(cut_ABC, [0, r, r+1, l])
                            omegas_ABC = [omega_tot_ABC, om['00'],
                                          om['0%s'%j], om['0%s'%j]]
                            start = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                            times_ABC = get_times(cut_ABC, [l+1, R, R+1])
                            omegas_ABC = [om['7%s'%j], om['7%s'%j], 
                                          om['77']]
                            end = get_ABC_inf_bis(trans_mat_ABC, times_ABC, omegas_ABC)
                            for i in [3, 5, 6]:
                                # 00 -> 0j -> ij -> 7j -> 77
                                res = vanloan_1(
                                    trans_mat_ABC,
                                    (om['0%s'%j], om['%s%s'%(i, j)]),
                                    om['0%s'%j], om['7%s'%j],
                                    cut_ABC[l+1]-cut_ABC[l])
                                ii = dct_num[i]
                                jj = dct_num[j]
                                tab[acc_tot] = [(ii, l, L), (jj, r, R), (pi@start@res@end).sum()]
                                acc_tot += 1
                                tab[acc_tot] = [(jj, r, R), (ii, l, L), tab[acc_tot-1][2]]
                                acc_tot += 1
                    else:
                        continue
    return tab