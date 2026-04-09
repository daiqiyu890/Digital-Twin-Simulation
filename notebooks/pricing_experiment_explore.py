#cd /Users/qiyudai/Documents/Github/Digital-Twin-Simulation

#



# Import pricing analysis functions directly
from evaluation.pricing_analysis import (
    load_randdollar_breakdown,
    prepare_purchase_data,
    calculate_relative_prices
)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

trial_dir = Path("text_simulation/text_simulation_output")

# Set up paths for pricing analysis
label_dir = trial_dir / "csv_comparison" / "csv_formatted_label"
randdollar_file = trial_dir / "csv_comparison" / "randdollar_breakdown.csv"
output_plot = trial_dir / "pricing_analysis_results" / "average_demand_curve.png"
output_plot.parent.mkdir(parents=True, exist_ok=True)

print("Running pricing demand curve analysis...")

# Check if randdollar file exists
if not randdollar_file.exists():
    print(f"⚠️  Missing required file: {randdollar_file.name}")
    print("   This file is generated during JSON to CSV conversion")
    print("   Skipping pricing analysis...")
else:
    try:
        # Load the randdollar breakdown data
        print("Loading randdollar breakdown data...")
        df_randdollar_breakdown = load_randdollar_breakdown(str(randdollar_file))
        
        if df_randdollar_breakdown is None or df_randdollar_breakdown.empty:
            print("⚠️  Could not load randdollar breakdown data")
        else:
            print(f"   Loaded {len(df_randdollar_breakdown)} price observations")
            
            # Prepare purchase data for each wave
            print("Preparing purchase data for each wave...")
            data_wave3 = prepare_purchase_data(df_randdollar_breakdown, "Wave1-3")
            data_wave4 = prepare_purchase_data(df_randdollar_breakdown, "Wave4")
            data_llm = prepare_purchase_data(df_randdollar_breakdown, "LLM_Imputed")
            
            # Combine all purchase data
            all_purchase_data = pd.concat([data_wave3, data_wave4, data_llm], ignore_index=True)
            
            if all_purchase_data.empty:
                print("⚠️  No purchase data could be processed")
            else:
                print(f"   Prepared {len(all_purchase_data)} purchase observations")
                
                # Calculate relative prices
                print("Calculating relative prices...")
                all_purchase_data, nprices = calculate_relative_prices(all_purchase_data)
                
                if nprices == 0:
                    print("⚠️  Could not determine price ranks - cannot generate demand curves")
                else:
                    print(f"   Found {nprices} distinct price points")
                    
                    # Compute demand curves
                    print("Computing demand curves...")
                    demand_curves = {}
                    for wave_name in ["Wave1-3", "Wave4", "LLM_Imputed"]:
                        current_wave_data = all_purchase_data[all_purchase_data["Wave"] == wave_name]
                        if not current_wave_data.empty:
                            curve = current_wave_data.groupby("Relative_Price_Rank")["Purchase"].mean()
                            # Reindex to ensure all price ranks from 1 to nprices are present
                            demand_curves[wave_name] = curve.reindex(range(1, nprices + 1), fill_value=np.nan)
                        else:
                            demand_curves[wave_name] = pd.Series([np.nan] * nprices, index=range(1, nprices + 1))
                    
                    # Create the plot
                    print("Creating demand curve plot...")
                    plt.figure(figsize=(10, 6))
                    x_axis = np.arange(1, nprices + 1)
                    
                    # Plot each wave's demand curve
                    if not demand_curves["Wave1-3"].isna().all():
                        plt.plot(x_axis, demand_curves["Wave1-3"], linestyle='-', marker='o', label='Wave 1-3')
                    if not demand_curves["Wave4"].isna().all():
                        plt.plot(x_axis, demand_curves["Wave4"], linestyle=':', marker='s', label='Wave 4')
                    if not demand_curves["LLM_Imputed"].isna().all():
                        plt.plot(x_axis, demand_curves["LLM_Imputed"], linestyle='-.', marker='^', label='LLM Imputed (Twins)')
                    
                    plt.ylim(0, 1)
                    plt.xticks(x_axis, fontsize=12)
                    plt.yticks(fontsize=12)
                    plt.xlabel('Relative Price Rank', fontsize=16)
                    plt.ylabel('Purchase Probability', fontsize=16)
                    plt.title('Average Demand Curve by Relative Price', fontsize=20)
                    plt.legend(fontsize=12, loc='best')
                    plt.grid(True, linestyle='--', alpha=0.7)
                    
                    # Save the plot
                    plt.savefig(str(output_plot), dpi=300, bbox_inches='tight')
                    plt.close()
                    
                    print(f"✅ Pricing analysis completed successfully")
                    print(f"   Demand curve plot saved to: {output_plot.name}")
                    
                    # Try to display the plot in the notebook
                    try:
                        from IPython.display import Image, display
                        display(Image(str(output_plot)))
                    except:
                        print("   (Plot saved but cannot display inline)")
                        
    except Exception as e:
        print(f"⚠️  Pricing analysis encountered an error: {e}")
        print("   This may be due to insufficient pricing data in the limited demo")
        print("   For full analysis, use the complete dataset with all personas")


