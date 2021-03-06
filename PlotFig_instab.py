# -*- coding: utf-8 -*-
"""
Created on Tue Jan  5 14:01:48 2016

@author: gabeo

Figure: activity and discriminability as approach instability
"""

''' Import libraries '''
import params; reload(params)
from generate_adj import generate_adj as gen_adj
from generate_adj import generate_regular_adj as gen_reg_adj
from degdist import degdist
from generate_W_lognormal import generate_W as gen_W

import sim_poisson
import numpy as np
import matplotlib.pyplot as plt
from raster import raster
from correlation_functions import auto_covariance_pop
from correlation_functions import bin_pop_spiketrain
from correlation_functions import cross_covariance_spk
from phi import phi_prime
from theory import rates_ss
from theory import rates_1loop
from theory import two_point_function_fourier_pop
from theory import two_point_function_fourier_pop_1loop
from theory import stability_matrix_1loop

import time
import os
import sys

start_time = time.time()

''' unpackage parameters '''

par = params.params()
Ne = par.Ne
Ni = par.Ni
N = par.N
pEE = par.pEE
pEI = par.pEI
pIE = par.pIE
pII = par.pII
tau = par.tau
b = par.b
gain = par.gain
weightEE = par.weightEE
weightEI = par.weightEI
weightIE = par.weightIE
weightII = par.weightII

Ntrials = 1
plot_raster = False

if plot_raster:
    tstop = 600. * tau
    Ncalc = 3
else:
    tstop = 6000. * tau
    # tstop = 10*tau
    Ncalc = 40  # 3 for rasters
dt = .005 * tau
trans = 5. * tau
window = tstop
Tmax = 8 * tau
dt_ccg = 1.
lags = np.arange(-Tmax, Tmax, dt_ccg)

''' output saving '''
rE_av_theory = np.zeros((Ncalc, Ntrials))


r_readout_theory = np.zeros((Ncalc, Ntrials))

rE_av_1loop = np.zeros((Ncalc, Ntrials))
r_readout_1loop = np.zeros((Ncalc, Ntrials))

if Ni > 0:
    rI_av_theory = np.zeros((Ncalc, Ntrials))
    rI_av_sim = np.zeros((Ncalc, Ntrials))
    rI_av_1loop = np.zeros((Ncalc, Ntrials))

spec_rad = np.zeros(Ncalc, )
spec_rad_1loop = np.zeros(Ncalc, )
two_point_integral_theory = np.zeros(Ncalc, )
two_point_integral_1loop = np.zeros(Ncalc, )
two_point_readout_theory = np.zeros((Ncalc, Ntrials))

two_point_integral_I_theory = np.zeros(Ncalc, )
two_point_integral_I_1loop = np.zeros(Ncalc, )
spec_rad_E = np.zeros(Ncalc, )
spec_rad_E_1loop = np.zeros(Ncalc, )
spec_rad_I = np.zeros(Ncalc, )
spec_rad_I_1loop = np.zeros(Ncalc, )

two_point_integral_I_sim = np.zeros((Ncalc, Ntrials))
two_point_Ipop_sim = np.zeros((Ncalc, Ntrials, lags.size))

two_point_integral_sim = np.zeros((Ncalc, Ntrials))
two_point_readout_sim = np.zeros((Ncalc, Ntrials, lags.size))
two_point_pop_sim = np.zeros((Ncalc, Ntrials, lags.size))
r_readout_sim = np.zeros((Ncalc, Ntrials))
rE_av_sim = np.zeros((Ncalc, Ntrials))
rI_av_sim = np.zeros((Ncalc, Ntrials))

if plot_raster:
    syn_scale = np.array((0., 20., 70.)) # for quadratic, was 75
    # syn_scale = np.array((0., 1., 12.)) # for linear
    # syn_scale = np.array((0., 1., 75.))  # for square root
    # syn_scale = np.array((0., 6., 20.))  # for quadratic E, linear I

else:
    # syn_scale = np.linspace(0., 85., Ncalc) # for quadratic
    # syn_scale = np.linspace(0., 12., Ncalc) # for linear
#     syn_scale = np.linspace(0, 100., Ncalc)  # for square root
#     syn_scale = np.linspace(0., 20., Ncalc)  # for quadratic E, linear I
    syn_scale = np.linspace(0, 95., Ncalc)

''' set save directory '''
if sys.platform == 'darwin': save_dir = '/Users/gocker/Documents/projects/field_theory_spiking/1loop_Ne=200_exponential_transfer/'
elif sys.platform == 'linux2': save_dir = '/local1/Documents/projects/field_theory_spiking/1loop_Ne=200_exponential_transfer/'

if not os.path.exists(save_dir):
    os.mkdir(save_dir)

''' load or generate adjacency matrix '''
W0_path = os.path.join(save_dir, 'W0.npy')

if os.path.exists(W0_path):
    W0 = np.load(W0_path)
else:

    W0 = gen_adj(Ne, Ni, pEE, pEI, pIE, pII)
#    W0EE = degdist(int(np.floor(Ne/10.)), Ne, .2, -1., pEE, .5, Ne)
#    W0[:Ne, :Ne] = W0EE

    # if Ne > 0: # make first neuron a readout
    #     W0[0, :] = 0
    #     W0[0, 1:Ne] = 1
    #     W0[:, 0] = 0

    np.save(W0_path, W0)

print('Ne=' + str(Ne) + ', Ni=' + str(Ni))

# Nstable = 38
Nstable = Ncalc

if not plot_raster:
    print 'computing theory'
    for nn in range(Ncalc):

        print 'progress %: ', float(nn)/float(Ncalc)*100

        ### generate scaled weight matrix from frozen connectivity realization
        W = W0 * 1.
        if Ne > 0:
            W[0:Ne, 0:Ne] = weightEE * W0[0:Ne, 0:Ne]
            W[Ne:, 0:Ne] = weightIE * W0[Ne:, 0:Ne]

        if Ni > 0:
            W[0:Ne, Ne:] = weightEI * W0[0:Ne, Ne:]
            W[Ne:, Ne:] = weightII * W0[Ne:, Ne:]

        W *= syn_scale[nn]
        # W[:Ne, :] *= syn_scale[nn]
        # W[Ne:, :] *= np.sqrt(syn_scale[nn])

#        if syn_scale[nn] > 0.:
#            W = gen_W(W0, Ne, syn_scale[nn]*weightEE, syn_scale[nn]*weightEE, syn_scale[nn]*weightEI, syn_scale[nn]*weightIE, syn_scale[nn]*weightII)
#        else:
#            W = np.zeros((N,N))

        r_th = rates_ss(W)
        rE_av_theory[nn] = np.mean(r_th[1:Ne]).real
        r_readout_theory[nn] = r_th[0].real

        r_th_11oop = rates_1loop(W)
        rE_av_1loop[nn] = np.mean(r_th_11oop[1:Ne]).real
        r_readout_1loop[nn] = r_th_11oop[0].real

        if Ni > 0:
           rI_av_1loop[nn] = np.mean(r_th_11oop[Ne:]).real
           rI_av_theory[nn] = np.mean(r_th[Ne:]).real
           two_point_integral_I_theory[nn] = np.real(two_point_function_fourier_pop(W, range(Ne, N))[0])
           two_point_integral_I_1loop[nn] = np.real(two_point_function_fourier_pop_1loop(W, range(Ne, N))[0])

        g = np.dot(W, r_th) + b
        w = 0.
        stab_mat_mft = np.dot(np.diag(phi_prime(g, gain)), W)
        stab_mat_1loop = stability_matrix_1loop(w, W, r_th)
        spec_rad[nn] = max(abs(np.linalg.eigvals(stab_mat_mft)))
        spec_rad_1loop[nn] = max(abs(np.linalg.eigvals(stab_mat_mft + stab_mat_1loop)))

        if spec_rad[nn] >= 1.:
            print 'mft unstable at wEE = ', weightEE
            Nstable = nn
            break

        spec_rad_E[nn] = max(abs(np.linalg.eigvals(stab_mat_mft[:Ne, :Ne])))
        spec_rad_E_1loop[nn] = max(abs(np.linalg.eigvals(stab_mat_mft[:Ne, :Ne] + stab_mat_1loop[:Ne, :Ne])))

        spec_rad_I[nn] = max(abs(np.linalg.eigvals(stab_mat_mft[Ne:, Ne:])))
        spec_rad_I_1loop[nn] = max(abs(np.linalg.eigvals(stab_mat_mft[Ne:, Ne:] + stab_mat_1loop[Ne:, Ne:])))

        two_point_integral_theory[nn] = np.real(two_point_function_fourier_pop(W, range(Ne))[0])
        two_point_integral_1loop[nn] = np.real(two_point_function_fourier_pop_1loop(W, range(Ne))[0])



print 'running sims'
if plot_raster:
    calc_range = range(Ncalc)
else:
    calc_range = range(0, Ncalc, 2)

for nn in calc_range:

    print 'progress %: ', float(nn) / float(Ncalc) * 100

    ### generate scaled weight matrix from frozen connectivity realization
    W = W0 * 1.
    if Ne > 0:
        W[0:Ne, 0:Ne] = weightEE * W0[0:Ne, 0:Ne]
        W[Ne:, 0:Ne] = weightIE * W0[Ne:, 0:Ne]

    if Ni > 0:
        W[0:Ne, Ne:] = weightEI * W0[0:Ne, Ne:]
        W[Ne:, Ne:] = weightII * W0[Ne:, Ne:]

    W *= syn_scale[nn]
#    if syn_scale[nn] > 0.:
#        W = gen_W(W0, Ne, syn_scale[nn] * weightEE, syn_scale[nn] * weightEE, syn_scale[nn] * weightEI,
#                  syn_scale[nn] * weightIE, syn_scale[nn] * weightII)
#    else:
#        W = np.zeros((N, N))

    # except:
   #     print 'mft unstable, % complete = ' + str(float(nn) / float(Ncalc) * 100)
    for nt in range(Ntrials):
        spktimes, g_vec, s_vec = sim_poisson.sim_poisson(W, tstop, trans, dt)

        ind_include = range(0, Ne)
        spk_Epop = bin_pop_spiketrain(spktimes, dt, 1, tstop, trans, ind_include)
        spk_readout = bin_pop_spiketrain(spktimes, dt, 1, tstop, trans, [0])
        # rE_av_sim[nn, nt] = np.sum(spk_Epop) / np.amax(spktimes[:, 0]) / float(len(ind_include))
        rE_av_sim[nn, nt] = np.sum(spk_Epop) / float(tstop-trans) / float(len(ind_include))

        r_readout_sim[nn, nt] = np.sum(spk_readout) / float(tstop - trans)

        two_point_readout_sim[nn, nt, :] = cross_covariance_spk(spktimes, spktimes.shape[0], 0, 0, dt, lags, tau,
                                                                tstop, trans)

        if Ni > 0:
            ind_include = range(Ne, N)
            spk_Ipop = bin_pop_spiketrain(spktimes, dt, 1, tstop, trans, ind_include)
            # rI_av_sim[nn, nt] = np.sum(spk_Ipop) / np.amax(spktimes[:, 0]) / float(len(ind_include))
            rI_av_sim[nn, nt] = np.sum(spk_Ipop) / float(tstop-trans) / float(len(ind_include))
            two_point_Ipop_sim[nn, nt, :] = auto_covariance_pop(spktimes, range(Ne, N), spktimes.shape[0], dt, lags,
                                                                tau,
                                                                tstop, trans)
            two_point_integral_I_sim[nn, nt] = np.sum(two_point_Ipop_sim[nn, nt, :]) * dt_ccg

        two_point_pop_sim[nn, nt, :] = auto_covariance_pop(spktimes, range(0, Ne), spktimes.shape[0], dt, lags, tau,
                                                           tstop, trans)
        two_point_integral_sim[nn, nt] = np.sum(two_point_pop_sim[nn, nt, :]) * dt_ccg

    if plot_raster and nn == 1 or plot_raster and nn == Ncalc - 1:
        print 'plotting raster'
        savefile = os.path.join(save_dir, 'raster_scale=' + str(syn_scale[nn]) + '.pdf')
        spktimes[:, 0] -= trans
        raster(spktimes, spktimes.shape[0], tstop, savefile, size=(1.875, 1.875))

        ind = (W0[0, :] == 1)
        gE = np.dot(W[0, :Ne], s_vec.T[:Ne])
        gI = np.dot(W[0, Ne:], s_vec.T[Ne:])

        savefile = os.path.join(save_dir, 'input_neuron0_scale='+ str(syn_scale[nn]) + '.pdf')
        size=(1.875, 1.875)
        fig = plt.figure(figsize=size)
        plt.plot(np.arange(0, tstop, dt), g_vec[:, 0]+1.5, 'k', linewidth=2, label='Total')
        plt.plot(np.arange(0, tstop, dt), gE, 'g', linewidth=2, label='Excitatory')
        plt.plot(np.arange(0, tstop, dt), gI, 'b', linewidth=2, label='Inhibitory')
        plt.legend(loc=0)
        plt.ylim((-4, 4))
        plt.xlim((0, 2000))
        plt.xlabel('Time (ms)')
        plt.ylabel('Synaptic input')

        plt.savefig(savefile)
        plt.close(fig)

        print 'plotting population two-point function'

end_time = time.time()
print end_time - start_time
#
syn_scale *= weightEE

# ''' Plot figures '''
# save_dir = os.path.join(save_dir, 'linear')
# if not os.path.exists(save_dir):
#     os.mkdir(save_dir)
if not plot_raster:

    # size = (2., .8)
    size = (5., .8)

    fig, ax = plt.subplots(1, figsize=size)
    ax.plot(syn_scale[:Nstable], rE_av_theory[:Nstable],  'k', label='Tree level', linewidth=2)
    if not 'linear' in save_dir: ax.plot(syn_scale[:Nstable], rE_av_theory[:Nstable]+rE_av_1loop[:Nstable], 'r' , label='One loop', linewidth=2);
    ax.plot(syn_scale[0:Ncalc:2], rE_av_sim[0:Ncalc:2], 'ko', label='Sim')
    ax.set_ylabel('E Population Rate (sp/ms)')
    ax.set_xlabel('Exc-exc Synaptic Weight (mV)')
    ax.set_xlim((0, np.amax(syn_scale)))
    ax.set_ylim((0, rE_av_theory[0]*2))
    # ax.legend(loc=0, fontsize=10)

    for item in ([ax.title, ax.xaxis.label, ax.yaxis.label]):
        item.set_fontsize(10)
        item.set_fontname('Arial')
    for item in (ax.get_xticklabels() + ax.get_yticklabels()):
        item.set_fontsize(8)
        item.set_fontname('Arial')

    savefile = os.path.join(save_dir, 'rE_vs_weight.pdf')
    fig.savefig(savefile)
    plt.show(fig)
    plt.close(fig)

    fig, ax = plt.subplots(1, figsize=size)
    ax.plot(syn_scale[:Nstable], r_readout_theory[:Nstable], 'k', label='Tree level', linewidth=2)
    if not 'linear' in save_dir: ax.plot(syn_scale[:Nstable], r_readout_theory[:Nstable] + r_readout_1loop[:Nstable], 'r', label='One loop', linewidth=2);
    ax.plot(syn_scale[0:Ncalc:2], r_readout_sim[0:Ncalc:2], 'ko', label='Sim')
    ax.set_ylabel('Readout Rate (sp/ms)')
    ax.set_xlabel('Exc-exc Synaptic Weight (mV)')
    ax.set_xlim((0, np.amax(syn_scale)))
    if 'quadratic' in save_dir:
        ax.set_ylim((0, r_readout_theory[0]*20))
    elif 'linear' in save_dir:
        ax.set_ylim((0, np.amax(r_readout_theory)*1.5))
    # ax.legend(loc=0, fontsize=10)

    for item in ([ax.title, ax.xaxis.label, ax.yaxis.label]):
        item.set_fontsize(10)
        item.set_fontname('Arial')
    for item in (ax.get_xticklabels() + ax.get_yticklabels()):
        item.set_fontsize(8)
        item.set_fontname('Arial')

    savefile = os.path.join(save_dir, 'r_readout_vs_weight.pdf')
    fig.savefig(savefile)
    plt.show(fig)
    plt.close(fig)

    if Ni>0:
        fig, ax = plt.subplots(1, figsize=size)
        ax.plot(syn_scale[:Nstable], rI_av_theory[:Nstable], 'k', label='Tree level', linewidth=2)
        if not 'linear' in save_dir: ax.plot(syn_scale[:Nstable], rI_av_theory[:Nstable] + rI_av_1loop[:Nstable], 'r', label='One loop',
                                             linewidth=2);
        ax.plot(syn_scale[0:Ncalc:2], rI_av_sim[0:Ncalc:2], 'ko', label='Sim')
        ax.set_ylabel('I Population Rate (sp/ms)')
        ax.set_xlabel('Exc-exc Synaptic Weight (mV)')
        ax.set_xlim((0, np.amax(syn_scale)))
        ax.set_ylim((0, rI_av_theory[0]*2))
        # ax.legend(loc=0, fontsize=10)

        for item in ([ax.title, ax.xaxis.label, ax.yaxis.label]):
            item.set_fontsize(10)
            item.set_fontname('Arial')
        for item in (ax.get_xticklabels() + ax.get_yticklabels()):
            item.set_fontsize(8)
            item.set_fontname('Arial')

        savefile = os.path.join(save_dir, 'rI_vs_weight.pdf')
        fig.savefig(savefile)
        plt.show(fig)
        plt.close(fig)


        fig, ax = plt.subplots(1, figsize=size)
        ax.plot(syn_scale[:Nstable], two_point_integral_I_theory[:Nstable], 'k', label='Tree level', linewidth=2)
        if not 'linear' in save_dir: ax.plot(syn_scale[:Nstable], two_point_integral_I_theory[:Nstable] + two_point_integral_I_1loop[:Nstable], 'r', label='One loop',
                                             linewidth=2);
        ax.plot(syn_scale[0:Ncalc:2], two_point_integral_I_sim[0:Ncalc:2], 'ko', label='Sim')
        ax.set_ylabel('I Pop. Spike Train Variance (sp^2/ms)')
        ax.set_xlabel('Exc-exc Synaptic Weight (mV)')
        ax.set_xlim((0, np.amax(syn_scale)))
        if 'quadratic' in save_dir:
            ax.set_ylim((0, two_point_integral_I_theory[0]*3))
        elif 'linear' in save_dir:
            ax.set_ylim((0, np.amax(two_point_integral_I_theory*1.5)))
        # ax.legend(loc=0, fontsize=10)

        for item in ([ax.title, ax.xaxis.label, ax.yaxis.label]):
            item.set_fontsize(10)
            item.set_fontname('Arial')
        for item in (ax.get_xticklabels() + ax.get_yticklabels()):
            item.set_fontsize(8)
            item.set_fontname('Arial')

        savefile = os.path.join(save_dir, 'var_Ipop_vs_weight.pdf')
        fig.savefig(savefile)
        plt.show(fig)
        plt.close(fig)

        fig, ax = plt.subplots(1, figsize=(4, 4))
        ind_norm = np.where(lags==0)[0]
        ax.plot(lags, two_point_Ipop_sim[4, 0, :] / two_point_Ipop_sim[4, 0, ind_norm], 'k', label=r'$W_{EE} = .05$')
        ax.plot(lags, two_point_Ipop_sim[10, 0, :] / two_point_Ipop_sim[10, 0, ind_norm], 'r', label=r'$W_{EE} = .13$')
        ax.plot(lags, two_point_Ipop_sim[24, 0, :] / two_point_Ipop_sim[24, 0, ind_norm], 'b', label=r'$W_{EE} = 0.3$')
        # ax.legend(loc=0, fontsize=10)
        ax.set_ylim((0, 1.))

        for item in ([ax.title, ax.xaxis.label, ax.yaxis.label]):
            item.set_fontsize(10)
            item.set_fontname('Arial')
        for item in (ax.get_xticklabels() + ax.get_yticklabels()):
            item.set_fontsize(8)
            item.set_fontname('Arial')

        savefile = os.path.join(save_dir, 'two_point_sim_I_norm.pdf')
        fig.savefig(savefile)
        plt.show(fig)
        plt.close(fig)


    fig, ax = plt.subplots(1, figsize=size)
    ax.plot(syn_scale[:Nstable], two_point_integral_theory[:Nstable], 'k', label='Tree level', linewidth=2)
    if not 'linear' in save_dir: ax.plot(syn_scale[:Nstable], two_point_integral_theory[:Nstable] + two_point_integral_1loop[:Nstable], 'r', label='One loop',
                                         linewidth=2);
    ax.plot(syn_scale[0:Ncalc:2], two_point_integral_sim[0:Ncalc:2], 'ko', label='Sim')
    ax.set_ylabel('E Pop. Spike Train Variance (sp/ms)^2')
    ax.set_xlabel('Exc-exc Synaptic Weight (mV)')
    ax.set_xlim((0, np.amax(syn_scale)))
    if 'quadratic' in save_dir:
        ax.set_ylim((0, two_point_integral_theory[0]*3))
    elif 'linear' in save_dir:
        ax.set_ylim((0, np.amax(two_point_integral_theory*1.5)))
    # ax.legend(loc=0, fontsize=10)

    for item in ([ax.title, ax.xaxis.label, ax.yaxis.label]):
        item.set_fontsize(10)
        item.set_fontname('Arial')
    for item in (ax.get_xticklabels() + ax.get_yticklabels()):
        item.set_fontsize(8)
        item.set_fontname('Arial')

    savefile = os.path.join(save_dir, 'var_Epop_vs_weight.pdf')
    fig.savefig(savefile)
    plt.show(fig)
    plt.close(fig)


    fig, ax = plt.subplots(1, figsize=size)
    ax.plot(syn_scale[:Nstable], spec_rad[:Nstable], 'k', label='Tree level', linewidth=2)
    if not 'linear' in save_dir:
        ax.plot(syn_scale[:Nstable], spec_rad_1loop[:Nstable], 'r', label='One loop', linewidth=2)

        ax.plot(syn_scale, np.ones(syn_scale.shape), 'k--')

    ax.set_ylabel('Spectral radius of mean field theory')
    ax.set_xlabel('Exc-exc Synaptic Weight (mV)')
    ax.set_xlim((0, np.amax(syn_scale)))
    ax.set_ylim((0, 1.5))
    # ax.legend(loc=0, fontsize=10)

    for item in ([ax.title, ax.xaxis.label, ax.yaxis.label]):
        item.set_fontsize(10)
        item.set_fontname('Arial')
    for item in (ax.get_xticklabels() + ax.get_yticklabels()):
        item.set_fontsize(8)
        item.set_fontname('Arial')

    savefile = os.path.join(save_dir, 'stability_vs_weight.pdf')
    fig.savefig(savefile)
    plt.show(fig)
    plt.close(fig)


    fig, ax = plt.subplots(1, figsize=size)
    ax.plot(syn_scale[:Nstable], spec_rad_E[:Nstable], 'k', label='Tree level', linewidth=2)
    if not 'linear' in save_dir:
        ax.plot(syn_scale[:Nstable], spec_rad_E_1loop[:Nstable],
                                         'r', label='One loop', linewidth=2)

        ax.plot(syn_scale, np.ones(syn_scale.shape), 'k--')

    ax.set_ylabel('Spectral radius of E-only mean field theory')
    ax.set_xlabel('Exc-exc Synaptic Weight (mV)')
    ax.set_xlim((0, np.amax(syn_scale)))
    ax.set_ylim((0, 1.5))
    # ax.legend(loc=0, fontsize=10)

    for item in ([ax.title, ax.xaxis.label, ax.yaxis.label]):
        item.set_fontsize(10)
        item.set_fontname('Arial')
    for item in (ax.get_xticklabels() + ax.get_yticklabels()):
        item.set_fontsize(8)
        item.set_fontname('Arial')

    savefile = os.path.join(save_dir, 'stability_Eonly_vs_weight.pdf')
    fig.savefig(savefile)
    plt.show(fig)
    plt.close(fig)


    fig, ax = plt.subplots(1, figsize=size)
    ax.plot(syn_scale[:Nstable], spec_rad_I[:Nstable], 'k', label='Tree level', linewidth=2)
    if not 'linear' in save_dir:
        ax.plot(syn_scale[:Nstable], spec_rad_I_1loop[:Nstable],
                                         'r', label='One loop', linewidth=2)

        ax.plot(syn_scale, np.ones(syn_scale.shape), 'k--')

    ax.set_ylabel('Spectral radius of I-only mean field theory')
    ax.set_xlabel('Exc-exc Synaptic Weight (mV)')
    ax.set_xlim((0, np.amax(syn_scale)))
    ax.set_ylim((0, 1.5))
    # ax.legend(loc=0, fontsize=10)

    for item in ([ax.title, ax.xaxis.label, ax.yaxis.label]):
        item.set_fontsize(10)
        item.set_fontname('Arial')
    for item in (ax.get_xticklabels() + ax.get_yticklabels()):
        item.set_fontsize(8)
        item.set_fontname('Arial')

    savefile = os.path.join(save_dir, 'stability_Ionly_vs_weight.pdf')
    fig.savefig(savefile)
    plt.show(fig)
    plt.close(fig)

    fig, ax = plt.subplots(1, figsize=(4, 4))
    ax.plot(lags, two_point_pop_sim[4, 0, :], 'k', label=r'$W_{EE} = .05$')
    ax.plot(lags, two_point_pop_sim[10, 0, :], 'r', label=r'$W_{EE} = .13$')
    ax.plot(lags, two_point_pop_sim[24, 0, :], 'b', label=r'$W_{EE} = 0.3$')
    ax.legend(loc=0, fontsize=10)

    for item in ([ax.title, ax.xaxis.label, ax.yaxis.label]):
        item.set_fontsize(10)
        item.set_fontname('Arial')
    for item in (ax.get_xticklabels() + ax.get_yticklabels()):
        item.set_fontsize(8)
        item.set_fontname('Arial')

    savefile = os.path.join(save_dir, 'two_point_sim.pdf')
    fig.savefig(savefile)
    plt.show(fig)
    plt.close(fig)

    fig, ax = plt.subplots(1, figsize=(4, 4))
    ind_norm = np.where(lags==0)[0]
    ax.plot(lags, two_point_pop_sim[4, 0, :] / two_point_pop_sim[4, 0, ind_norm], 'k', label=r'$W_{EE} = .05$')
    ax.plot(lags, two_point_pop_sim[10, 0, :] / two_point_pop_sim[10, 0, ind_norm], 'r', label=r'$W_{EE} = .13$')
    ax.plot(lags, two_point_pop_sim[24, 0, :] / two_point_pop_sim[24, 0, ind_norm], 'b', label=r'$W_{EE} = 0.3$')
    # ax.legend(loc=0, fontsize=10)
    ax.set_ylim((0, 1.))

    for item in ([ax.title, ax.xaxis.label, ax.yaxis.label]):
        item.set_fontsize(10)
        item.set_fontname('Arial')
    for item in (ax.get_xticklabels() + ax.get_yticklabels()):
        item.set_fontsize(8)
        item.set_fontname('Arial')

    savefile = os.path.join(save_dir, 'two_point_sim_norm.pdf')
    fig.savefig(savefile)
    plt.show(fig)
    plt.close(fig)

    ''' save data '''

    savefile = os.path.join(save_dir, 'rE_av_sim.npy')
    np.save(savefile, rE_av_sim)

    savefile = os.path.join(save_dir, 'r_readout_sim.npy')
    np.save(savefile, r_readout_sim)

    savefile = os.path.join(save_dir, 'rI_av_sim.npy')
    np.save(savefile, rI_av_sim)

    savefile = os.path.join(save_dir, 'two_point_pop_sim.npy')
    np.save(savefile, two_point_pop_sim)

    savefile = os.path.join(save_dir, 'two_point_Ipop_sim.npy')
    np.save(savefile, two_point_Ipop_sim)

    savefile = os.path.join(save_dir, 'two_point_readout_sim.npy')
    np.save(savefile, two_point_readout_sim)

    savefile = os.path.join(save_dir, 'two_point_integral_sim.npy')
    np.save(savefile, two_point_integral_sim)

    savefile = os.path.join(save_dir, 'two_point_integral_I_sim.npy')
    np.save(savefile, two_point_integral_I_sim)

    savefile = os.path.join(save_dir, 'rE_av_theory.npy')
    np.save(savefile, rE_av_theory)

    savefile = os.path.join(save_dir, 'r_readout_theory.npy')
    np.save(savefile, r_readout_theory)

    savefile = os.path.join(save_dir, 'rI_av_theory.npy')
    np.save(savefile, rI_av_theory)

    savefile = os.path.join(save_dir, 'rE_av_1loop.npy')
    np.save(savefile, rE_av_1loop)

    savefile = os.path.join(save_dir, 'r_readout_1loop.npy')
    np.save(savefile, r_readout_1loop)

    savefile = os.path.join(save_dir, 'rI_av_1loop.npy')
    np.save(savefile, rI_av_1loop)

    savefile = os.path.join(save_dir, 'two_point_integral_theory.npy')
    np.save(savefile, two_point_integral_theory)

    savefile = os.path.join(save_dir, 'two_point_integral_1loop.npy')
    np.save(savefile, two_point_integral_1loop)

    savefile = os.path.join(save_dir, 'two_point_integral_I_theory.npy')
    np.save(savefile, two_point_integral_I_theory)

    savefile = os.path.join(save_dir, 'two_point_integral_I_1loop.npy')
    np.save(savefile, two_point_integral_I_1loop)

    savefile = os.path.join(save_dir, 'spec_rad.npy')
    np.save(savefile, spec_rad)

    savefile = os.path.join(save_dir, 'spec_rad_1loop.npy')
    np.save(savefile, spec_rad_1loop)

    savefile = os.path.join(save_dir, 'spec_rad_E.npy')
    np.save(savefile, spec_rad_E)

    savefile = os.path.join(save_dir, 'spec_rad_E_1loop.npy')
    np.save(savefile, spec_rad_E_1loop)

    savefile = os.path.join(save_dir, 'spec_rad_I.npy')
    np.save(savefile, spec_rad_I)

    savefile = os.path.join(save_dir, 'spec_rad_I_1loop.npy')
    np.save(savefile, spec_rad_I_1loop)

print syn_scale
print syn_scale/weightEE