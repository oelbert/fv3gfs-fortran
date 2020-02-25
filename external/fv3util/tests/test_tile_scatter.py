import pytest
import numpy as np
from utils import DummyComm
import fv3util


def rank_scatter_results(communicator_list, quantity):
    for rank, tile_communicator in enumerate(communicator_list):
        if rank == 0:
            array = quantity
        else:
            array = None
        metadata = fv3util.QuantityMetadata.from_quantity(quantity)
        yield tile_communicator, tile_communicator.scatter_tile(metadata, send_quantity=array)


def get_tile_communicator_list(partitioner):
    total_ranks = partitioner.layout[0] * partitioner.layout[1]
    shared_buffer = {}
    tile_communicator_list = []
    for rank in range(total_ranks):
        tile_communicator_list.append(
            fv3util.TileCommunicator(
                tile_comm=DummyComm(
                    rank=rank, total_ranks=total_ranks, buffer_dict=shared_buffer
                ),
                partitioner=partitioner,
            )
        )
    return tile_communicator_list


@pytest.mark.parametrize(
    'layout', [(1, 1), (1, 2), (2, 1), (2, 2), (3, 3)]
)
def test_interface_state_two_by_two_per_rank_scatter_tile(layout):
    nz = 5
    ny = layout[0]
    nx = layout[1]
    state = {
        'pos_j': fv3util.Quantity(
            np.empty([layout[0] + 1, layout[1] + 1]),
            dims=[fv3util.Y_INTERFACE_DIM, fv3util.X_INTERFACE_DIM],
            units='dimensionless',
        ),
        'pos_i': fv3util.Quantity(
            np.empty([layout[0] + 1, layout[1] + 1], dtype=np.int32),
            dims=[fv3util.Y_INTERFACE_DIM, fv3util.X_INTERFACE_DIM],
            units='dimensionless',
        ),
    }
    
    state['pos_j'].view[:, :] = np.arange(0, layout[0] + 1)[:, None]
    state['pos_i'].view[:, :] = np.arange(0, layout[1] + 1)[None, :]

    partitioner = fv3util.Partitioner(nz, ny, nx, layout)
    tile_communicator_list = get_tile_communicator_list(partitioner)
    for communicator, rank_array in rank_scatter_results(tile_communicator_list, state['pos_j']):
        assert rank_array.extent == (2, 2)
        j, i = partitioner.subtile_index(communicator.rank)
        assert rank_array.view[0, 0] == j
        assert rank_array.view[0, 1] == j
        assert rank_array.view[1, 0] == j + 1
        assert rank_array.view[1, 1] == j + 1
        assert rank_array.data.dtype == state['pos_j'].data.dtype

    for communicator, rank_array in rank_scatter_results(tile_communicator_list, state['pos_i']):
        assert rank_array.extent == (2, 2)
        j, i = partitioner.subtile_index(communicator.rank)
        assert rank_array.view[0, 0] == i
        assert rank_array.view[1, 0] == i
        assert rank_array.view[0, 1] == i + 1
        assert rank_array.view[1, 1] == i + 1
        assert rank_array.data.dtype == state['pos_i'].data.dtype


@pytest.mark.parametrize(
    'layout', [(1, 1), (1, 2), (2, 1), (2, 2), (3, 3)]
)
def test_centered_state_one_item_per_rank_scatter_tile(layout):
    nz = 5
    ny = layout[0]
    nx = layout[1]
    total_ranks = layout[0] * layout[1]
    state = {
        'rank': fv3util.Quantity(
            np.empty([layout[0], layout[1]]),
            dims=[fv3util.Y_DIM, fv3util.X_DIM],
            units='dimensionless',
        ),
        'rank_pos_j': fv3util.Quantity(
            np.empty([layout[0], layout[1]]),
            dims=[fv3util.Y_DIM, fv3util.X_DIM],
            units='dimensionless',
        ),
        'rank_pos_i': fv3util.Quantity(
            np.empty([layout[0], layout[1]]),
            dims=[fv3util.Y_DIM, fv3util.X_DIM],
            units='dimensionless',
        ),
    }
    
    partitioner = fv3util.Partitioner(nz, ny, nx, layout)
    for rank in range(total_ranks):
        state['rank'].view[np.unravel_index(rank, state['rank'].extent)] = rank
        j, i = partitioner.subtile_index(rank)
        state['rank_pos_j'].view[np.unravel_index(rank, state['rank_pos_j'].extent)] = j
        state['rank_pos_i'].view[np.unravel_index(rank, state['rank_pos_i'].extent)] = i

    partitioner = fv3util.Partitioner(nz, ny, nx, layout)
    tile_communicator_list = get_tile_communicator_list(partitioner)
    for communicator, rank_array in rank_scatter_results(tile_communicator_list, state['rank']):
        assert rank_array.extent == (1, 1)
        assert rank_array.view[0, 0] == communicator.rank
        assert rank_array.data.dtype == state['rank'].data.dtype


@pytest.mark.parametrize(
    'layout', [(1, 1), (1, 2), (2, 1), (2, 2), (3, 3)]
)
@pytest.mark.parametrize(
    'n_halo', [0, 1, 3]
)
def test_centered_state_one_item_per_rank_with_halo_scatter_tile(layout, n_halo):
    nz = 5
    ny = layout[0]
    nx = layout[1]
    total_ranks = layout[0] * layout[1]
    state = {
        'rank': fv3util.Quantity(
            np.empty([layout[0] + 2 * n_halo, layout[1] + 2 * n_halo]),
            dims=[fv3util.Y_DIM, fv3util.X_DIM],
            units='dimensionless',
            origin=(n_halo, n_halo),
            extent=(ny, nx),
        ),
        'rank_pos_j': fv3util.Quantity(
            np.empty([layout[0] + 2 * n_halo, layout[1] + 2 * n_halo]),
            dims=[fv3util.Y_DIM, fv3util.X_DIM],
            units='dimensionless',
            origin=(n_halo, n_halo),
            extent=(ny, nx),
        ),
        'rank_pos_i': fv3util.Quantity(
            np.empty([layout[0] + 2 * n_halo, layout[1] + 2 * n_halo]),
            dims=[fv3util.Y_DIM, fv3util.X_DIM],
            units='dimensionless',
            origin=(n_halo, n_halo),
            extent=(ny, nx),
        ),
    }
    
    partitioner = fv3util.Partitioner(nz, ny, nx, layout)
    for rank in range(total_ranks):
        state['rank'].view[np.unravel_index(rank, state['rank'].extent)] = rank
        j, i = partitioner.subtile_index(rank)
        state['rank_pos_j'].view[np.unravel_index(rank, state['rank_pos_j'].extent)] = j
        state['rank_pos_i'].view[np.unravel_index(rank, state['rank_pos_i'].extent)] = i

    tile_communicator_list = get_tile_communicator_list(partitioner)
    for communicator, rank_array in rank_scatter_results(tile_communicator_list, state['rank']):
        assert rank_array.extent == (1, 1)
        assert rank_array.data[0, 0] == communicator.rank
        assert rank_array.data.dtype == state['rank'].data.dtype

