-- SPDX-License-Identifier: BSD-3-Clause
-- Binary counter on four LEDs of a Tang Primer 20K dock.
library ieee;
  use ieee.std_logic_1164.all;
  use ieee.numeric_std.all;

entity blinky is
  generic (
    g_WIDTH : positive := 27
  );
  port (
    clk : in    std_logic;
    led : out   std_logic_vector(3 downto 0)
  );
end entity blinky;

architecture rtl of blinky is

  signal count : unsigned(g_WIDTH - 1 downto 0) := (others => '0');

begin

  process (clk) is
  begin
    if rising_edge(clk) then
      count <= count + 1;
    end if;
  end process;

  led <= std_logic_vector(count(g_WIDTH - 1 downto g_WIDTH - 4));

  -- psl default clock is rising_edge(clk);
  -- psl assert_increments: assert always (next (count = prev(count) + 1));

end architecture rtl;
