import pandas as pd
import numpy as np

def calculate_playoff_prob(pf, league_avg_pf, wins, losses):
    """Calculates Playoff Probability using Pythagorean expectation."""
    if pf == 0:
        return "0.0%"
    
    total_games = wins + losses
    if total_games == 0:
        return "50.0%"
    
    exp_win_pct = (pf ** 3) / ((pf ** 3) + (league_avg_pf ** 3))
    current_win_pct = wins / total_games
    
    games_left = 28 - total_games
    blended_prob = ((current_win_pct * total_games) + (exp_win_pct * games_left)) / 28.0
    
    if blended_prob >= 0.99:
        blended_prob = 0.999
    elif blended_prob <= 0.01:
        blended_prob = 0.001
        
    return f"{round(blended_prob * 100, 1)}%"

def run_standings_pipeline(input_csv, output_csv):
    print("--- Running Fantasy Football Standings Pipeline ---")
    
    # 1. Load Raw Schedule Data
    df_raw = pd.read_csv(input_csv)
    
    # Hardcode Teams & Divisions so the script is immune to CSV formatting changes
    teams_metadata = {
        'TEAM 1': 'Baker', 'TEAM 2': 'Adams', 'TEAM 3': 'Adams', 
        'TEAM 4': 'Rainier', 'TEAM 5': 'Rainier', 'TEAM 6': 'Baker', 
        'TEAM 7': 'Baker', 'TEAM 8': 'Baker', 'TEAM 9': 'Rainier', 
        'TEAM 10': 'Adams', 'TEAM 11': 'Adams', 'TEAM 12': 'Rainier'
    }

    # Initialize Standings Tracker
    standings = {
        team: {'Division': div, 'W': 0, 'L': 0, 'Div_W': 0, 'Div_L': 0, 'PF': 0.0, 'PA': 0.0}
        for team, div in teams_metadata.items()
    }

    # Clean the schedule (ignores empty rows in the Team columns)
    schedule_df = df_raw.dropna(subset=[df_raw.columns[1], df_raw.columns[4]])
    
    # 2. Process Matchups & Scores
    np.random.seed(42)  # Generates consistent mock scores if blank
    
    for week_num, week_matches in schedule_df.groupby(schedule_df.columns[0]):
        weekly_scores = []
        
        for idx, row in week_matches.iterrows():
            t1, t2 = str(row.iloc[1]).strip().upper(), str(row.iloc[4]).strip().upper()
            
            # Skip if team isn't in our 12-team dictionary
            if t1 not in standings or t2 not in standings:
                continue
                
            # Use real score if it exists, otherwise generate a mock score
            s1 = round(np.random.normal(110, 15), 2) if pd.isna(row.iloc[2]) or str(row.iloc[2]).strip() == '' else float(row.iloc[2])
            s2 = round(np.random.normal(110, 15), 2) if pd.isna(row.iloc[3]) or str(row.iloc[3]).strip() == '' else float(row.iloc[3])
            
            weekly_scores.append((t1, s1))
            weekly_scores.append((t2, s2))
            
            same_div = standings[t1]['Division'] == standings[t2]['Division']
            standings[t1]['PF'] += s1; standings[t1]['PA'] += s2
            standings[t2]['PF'] += s2; standings[t2]['PA'] += s1
            
            # Head-to-Head Tally
            if s1 > s2:
                standings[t1]['W'] += 1; standings[t2]['L'] += 1
                if same_div: standings[t1]['Div_W'] += 1; standings[t2]['Div_L'] += 1
            elif s2 > s1:
                standings[t2]['W'] += 1; standings[t1]['L'] += 1
                if same_div: standings[t2]['Div_W'] += 1; standings[t1]['Div_L'] += 1

        # Weekly Median Tally
        if weekly_scores:
            scores_only = [s for _, s in weekly_scores]
            median_val = np.median(scores_only)
            
            for team, score in weekly_scores:
                if score >= median_val:
                    standings[team]['W'] += 1
                else:
                    standings[team]['L'] += 1

    # 3. Format Output Table & Compute Metrics
    out_df = pd.DataFrame.from_dict(standings, orient='index').reset_index()
    out_df.rename(columns={'index': 'Manager'}, inplace=True)
    out_df['PF'] = out_df['PF'].round(2)
    out_df['PA'] = out_df['PA'].round(2)
    
    league_avg_pf = out_df['PF'].mean()
    out_df['Playoff_Prob'] = out_df.apply(
        lambda r: calculate_playoff_prob(r['PF'], league_avg_pf, r['W'], r['L']), axis=1
    )
    
    # Sort by Total Wins, then Points For
    out_df = out_df.sort_values(by=['W', 'PF'], ascending=[False, False]).reset_index(drop=True)
    out_df.index += 1
    out_df.index.name = 'Seed'
    
    out_df.to_csv(output_csv)
    print(f"Standings successfully generated and saved to {output_csv}!")

if __name__ == "__main__":
    run_standings_pipeline('Input.csv', 'final_standings.csv')