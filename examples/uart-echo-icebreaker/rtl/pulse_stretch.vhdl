-- SPDX-License-Identifier: BSD-3-Clause
-- Holds `active` high for g_CYCLES clocks after each `trigger` pulse.
library ieee;
  use ieee.std_logic_1164.all;

entity pulse_stretch is
  generic (
    g_CYCLES : positive := 600_000
  );
  port (
    clk     : in    std_logic;
    trigger : in    std_logic;
    active  : out   std_logic
  );
end entity pulse_stretch;

architecture rtl of pulse_stretch is

  signal count : natural range 0 to g_CYCLES := 0;

begin

  process (clk) is
  begin
    if rising_edge(clk) then
      if trigger = '1' then
        count <= g_CYCLES;
      elsif count /= 0 then
        count <= count - 1;
      end if;
    end if;
  end process;

  active <= '1' when count /= 0 else '0';

  -- psl default clock is rising_edge(clk);
  -- psl assert_trigger_lights: assert always (trigger = '1' -> next (active = '1'));
  -- psl assert_idle_dark: assert always ((active = '0' and trigger = '0') -> next (active = '0'));

end architecture rtl;
