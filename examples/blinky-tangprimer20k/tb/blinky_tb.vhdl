-- SPDX-License-Identifier: BSD-3-Clause
library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity blinky_tb is
end entity blinky_tb;

architecture sim of blinky_tb is

  signal clk  : std_logic := '0';
  signal led  : std_logic_vector(3 downto 0);
  signal done : boolean   := false;

begin

  clk <= not clk after 18.5 ns when not done;

  dut : entity work.blinky
    generic map (
      g_WIDTH => 6
    )
    port map (
      clk => clk,
      led => led
    );

  check : process is
  begin
    wait for 1 ns;
    for i in 0 to 7 loop
      assert unsigned(led) = i
        report "FAIL: led pattern " & to_hstring(led)
        severity failure;
      for c in 1 to 4 loop
        wait until rising_edge(clk);
      end loop;
      wait for 1 ns;
    end loop;
    report "PASS: blinky counts";
    done <= true;
    wait;
  end process check;

end architecture sim;
