from copy import copy

import pandas as pd

ELECTIONS = 25
FOLDER = f'elec{ELECTIONS}'
folder_module = __import__(FOLDER)
surplus_agreements_module = getattr(folder_module, 'SurplusAgreement')
REDUNDANT_COLUMNS = ['סמל ועדה', 'שם ישוב', 'סמל ישוב', 'בזב', 'מצביעים', 'פסולים', 'כשרים']
DEBUG = False


def print_debug(string):
    if DEBUG:
        print(string)


def convert_file_to_df_and_clean(filename):
    # df = pd.read_csv(f'{FOLDER}/{filename}', encoding='mbcs')
    df = pd.read_csv(f'{FOLDER}/{filename}')
    columns_to_drop = [col for col in REDUNDANT_COLUMNS if col in df.columns]
    df = df.drop(columns=columns_to_drop)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    return df


def calc_mandates_1st_stage(results, seats=120):
    total_relevant_votes = sum(results.values())
    print_func = print if seats == 120 else print_debug
    print_func(f'total relevant votes: {total_relevant_votes}')
    votes_per_seat = total_relevant_votes/seats
    print_func(f'votes per seat: {votes_per_seat}')
    mandates_res = {}
    for party, votes in results.items():
        mandates_res[party] = int(votes/votes_per_seat)
    return mandates_res


def get_surplus_mandates_and_votes(p_mandates, p_votes):
    surplus_agreements = getattr(surplus_agreements_module, 'surplus_agreements')
    surplus_mandates = {}
    surplus_votes = {}
    parties_in_surplus= []
    for surplus_agreement in surplus_agreements.items():
        party_1 = surplus_agreement[0]
        party_2 = surplus_agreement[1]
        if party_1 in p_mandates.keys() and party_2 in p_mandates.keys():
            parties_in_surplus.append(party_1)
            parties_in_surplus.append(party_2)
            dict_key = f'{party_1} + {party_2}'
            value_mandates = p_mandates.get(party_1, 0) + p_mandates.get(party_2, 0)
            value_votes = p_votes.get(party_1, 0) + p_votes.get(party_2, 0)
            surplus_mandates[dict_key] = value_mandates
            surplus_votes[dict_key] = value_votes
    for party in [key for key in p_mandates.keys() if key not in parties_in_surplus]:
        surplus_mandates[party] = p_mandates[party]
        surplus_votes[party] = p_votes[party]
    return surplus_mandates, surplus_votes


def calc_bader_ofer(p_mandates, p_votes, p_total_mandates=120):
    print_debug(f'calculating Bader-Ofer for {p_total_mandates} mandates:')
    mandates = p_mandates
    calc_round = 0
    total_mandates = sum(mandates.values())
    while total_mandates < p_total_mandates and calc_round < p_total_mandates:
        votes_per_future_mandate = dict(map(lambda party_, votes_, mandates_: (party_, votes_/(mandates_ + 1)),
                                            p_votes.keys(), p_votes.values(), mandates.values()))
        print_debug(f'votes_per_future_mandate: {votes_per_future_mandate}')
        party_to_get_mandate = max(votes_per_future_mandate, key=votes_per_future_mandate.get)
        print_debug(f'party_to_get_mandate: {party_to_get_mandate}')
        mandates[party_to_get_mandate] += 1
        total_mandates = sum(mandates.values())
        calc_round += 1
        print_debug(f'total mandates after {calc_round} rounds: {total_mandates}')
    return mandates


def split_surplus_mandates(p_surplus_mandates_distro, p_votes):
    print_debug(p_surplus_mandates_distro)
    mandates_distro = copy(p_surplus_mandates_distro)
    for surplus_parties, surplus_mandates in p_surplus_mandates_distro.items():
        if '+' in surplus_parties:
            print_debug(f'calculating split of {surplus_parties}, who have {surplus_mandates} mandates')
            mandates_distro.pop(surplus_parties)
            party1, party2 = surplus_parties.split(' + ')
            surplus_votes_dict = {party1: p_votes[party1], party2: p_votes[party2]}
            mandates_calc_1st_stage = calc_mandates_1st_stage(surplus_votes_dict, surplus_mandates)
            print_debug(f'after 1st stage, the result is {mandates_calc_1st_stage}')
            mandates_distro[party1] = mandates_calc_1st_stage[party1]
            mandates_distro[party2] = mandates_calc_1st_stage[party2]
            if sum(mandates_calc_1st_stage.values()) < surplus_mandates:
                surplus_mandates_dict = {party1: mandates_distro[party1], party2: mandates_distro[party2]}
                surplus_mandates_final = calc_bader_ofer(surplus_mandates_dict,
                                                         surplus_votes_dict,
                                                         p_surplus_mandates_distro[surplus_parties])
                print_debug(f'after 2nd stage, the result is {surplus_mandates_final}')
                mandates_distro[party1] = surplus_mandates_final[party1]
                mandates_distro[party2] = surplus_mandates_final[party2]
    return mandates_distro


def calc_elections_result():
    clean_df = convert_file_to_df_and_clean('expc.csv')
    all_results = clean_df.sum().to_dict()
    print(f'all results: {all_results}')
    valid_votes = clean_df.sum().sum()
    print(f'valid votes: {valid_votes}')
    pass_percentage_votes = valid_votes / 100 * 3.25
    print(f'pass percentage votes: {pass_percentage_votes}')
    relevant_votes = dict(filter(lambda item: item[1] >= pass_percentage_votes, all_results.items()))
    print(f'relevant votes: {relevant_votes}')
    mandates_distro = calc_mandates_1st_stage(relevant_votes)
    print(f'mandates distribution after 1st stage: {mandates_distro}')
    total_mandates = sum(mandates_distro.values())
    print(f'total mandates after 1st stage: {total_mandates}')
    print_debug('-----------------------------------')
    if total_mandates < 120:
        surplus_mandates_distro, surplus_votes = get_surplus_mandates_and_votes(mandates_distro, relevant_votes)
        print(f'surplus mandates distribution: {surplus_mandates_distro}')
        surplus_mandates_distro = calc_bader_ofer(surplus_mandates_distro, surplus_votes)
        print(f'surplus mandates distribution after Bader-Ofer: {surplus_mandates_distro}')
        if len(surplus_mandates_distro) < len(mandates_distro):
            mandates_distro = split_surplus_mandates(surplus_mandates_distro, relevant_votes)
            print(f'FINAL MANDATES DISTRIBUTION: {mandates_distro}')


if __name__ == '__main__':
    calc_elections_result()


